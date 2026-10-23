# Image and animation asset workflow research

**Status:** Research notes, not an implementation decision. Reviewed 2026-10-23.

## Summary

The supplied direction is a good fit for this project: keep editable artwork and animation metadata as the authoring inputs, and let a host-side converter produce a compact format for the ESP32. Avoid making hand-arranged sprite sheets the format people must author. A sheet can still be an import or packing format when it has metadata that maps frames.

The recently flashed `t3/optional-pages-screensaver` prototype (`ed6355a`) contains a procedural companion face and a text-only Images placeholder. It has no image importer, asset converter, or frame playback engine yet. This note describes options for a later asset pipeline; it does not change that prototype's scope.

## Procedural screensaver scene ideas

The supplied TFT_eSPI sketch suggests a second, independent path for optional screensaver content: generate scenes with drawing primitives on the ESP32, without source images or a conversion pipeline. The two candidate scenes are:

- **Starfield:** stars move outward from a vanishing point with perspective streaks and a dark gradient background.
- **Tiny living world:** a synthwave sunset, layered mountains and city, blinking windows, a moving hover pod, rain, and a neon perspective road.

These are exploratory scene concepts, not selected designs. If pursued, they should integrate as scene renderers in the existing page/screensaver framework, rather than becoming a separate Arduino sketch. Scene selection and page visibility belong in build-time configuration, consistent with the earlier optional-pages request. Procedural rendering does not need the image importer described below; the future engine may share page lifecycle and timing conventions while keeping drawing code separate from frame-based assets.

### Memory and frame-rate constraints

The example's 16-bit full-screen buffer arithmetic is correct: 240×240×2 = 115,200 bytes; 320×240×2 = 153,600 bytes. The current firmware renderer uses a single 320×240 8-bit buffer (76,800 bytes). A single 16-bit canvas would add about 76,800 bytes over that buffer; a second 16-bit full-screen buffer would add another 153,600 bytes. Reusing the existing canvas is therefore the initial option to investigate, subject to color-depth and renderer compatibility.

The sketch's 30 FPS is a target cap, not evidence that the board can sustain that rate. At the project's configured 40 MHz SPI clock, transferring a 320×240 RGB565 frame alone takes a theoretical minimum of 30.72 ms (153,600 bytes × 8 ÷ 40,000,000 bits/s), leaving only about 2.6 ms of a 33.3 ms frame interval for rendering and driver overhead. Actual transfer time will be longer. The per-row gradient, many city-window primitives, and road/rain drawing also consume CPU time. Measure on the device before choosing a frame cap or pixel format; a lower rate or partial updates may be needed.

### Candidate implementation plan

1. Prototype each scene as an optional renderer using the existing framebuffer and page lifecycle; keep telemetry views responsive and the existing screensaver-off default.
2. Start with a modest starfield and tiny-world scene, with compile-time selection/configuration and normal page navigation when enabled. Keep the user's chosen page as the screensaver target configurable at build time.
3. Build each configuration and inspect on-device framebuffer captures. Record free heap and measured frame durations/FPS, including page changes and wake behavior when screensaver mode is enabled.
4. Tune scene complexity and frame pacing from those measurements. Only consider RGB565 or another buffering strategy if color quality or measured performance requires it.

Open implementation choices remain: one configurable procedural-scene page versus separate pages, whether the current RGB332 buffer can serve both scenes adequately, and what frame-rate target is comfortable on the actual board. No code or runtime evidence for these scenes has been added yet.

## Authoring inputs and metadata

An accessible first format is named PNG frames organized by animation state, paired with a manifest. For example, an artist can keep separate `idle/` and `walk/` frame folders and list their frames in `animation.json`. Static images can be represented as one-frame animations. Keep original source art alongside generated runtime output so it remains editable.

The manifest should identify frame order and playback properties rather than requiring people to calculate atlas coordinates. Candidate fields include animation name, source paths, frame dimensions, per-frame duration, loop behavior, anchor/pivot, and trim offsets. A default FPS can make constant-rate animations concise, but per-frame durations are needed to preserve source timing where frames have different delays. These fields are research recommendations; the schema is not settled.

Aseprite can export sprite sheets and JSON metadata from the command line. Its CLI also supports exporting frames as separate files, selecting tagged frames, splitting tags, and merging duplicate frames. This makes `.ase`/`.aseprite` files a possible optional importer without making sprite-sheet coordinates the hand-authored format. When consuming a packed sheet, require its metadata; do not infer frame locations from image dimensions. [Aseprite sprite-sheet guide](https://www.aseprite.org/docs/sprite-sheet/) · [Aseprite CLI export options](https://www.aseprite.org/docs/cli/)

## Candidate conversion and playback pipeline

```text
Editable sources + animation manifest
               |
       Host-side importer(s)
               |
 Validate, order, time, trim, and map frames
               |
 Convert to a measured firmware pixel format
               |
 Generated frame data + playback metadata
               |
       ESP32 animation player
```

Separate importers can support PNG sequences, static images, Aseprite exports, and later GIF files. They should normalize into one frame-and-timing representation before generating firmware data. This keeps file-format decoding and validation on the PC, while the ESP32 handles playback, frame timing, loops, positioning, transparency, and transitions. Procedural renderers can share playback timing/state concepts but continue to draw with C++ rather than being converted into image frames.

GIF can be decoded during conversion rather than on the device. LVGL is one alternative runtime framework, and its current GIF widget accepts embedded image descriptors or files (with a registered filesystem driver for file paths). Its documentation estimates about 25 kB of RAM plus `(pixel size + 1) × width × height` for a GIF framebuffer. At 320×240 RGB565, that estimate is roughly 255 kB, before this project's existing framebuffer. Since the flashed prototype reported about 240 kB free heap after allocating its framebuffer, this suggests full-screen GIF playback through LVGL would not fit without major memory changes; that is an estimate, not a measurement of a custom player. This repo uses TFT_eSPI and a custom renderer, not LVGL; adopting LVGL solely for GIF playback would add a separate rendering stack and should be compared with offline conversion first. [LVGL GIF widget documentation](https://github.com/lvgl/lvgl/blob/master/docs/src/widgets/gif.mdx)

## Fit with this board and firmware

- The documented ESP32-2432S024C has 4 MB flash and no PSRAM reported on the tested unit. The normal renderer allocates a 320×240, 8-bit RGB332 framebuffer: 76,800 bytes. See [hardware details](HARDWARE.md).
- The T-001 prototype build reported 414,019 bytes of firmware in the default 1,310,720-byte application partition. That leaves about 897 kB of partition space at that build, shared with firmware code and all compiled assets; it is not a per-animation allowance.
- A raw 32×32 frame is 1,024 bytes at 8 bits per pixel or 2,048 bytes at 16 bits per pixel, before transparency or metadata. Thirty-two such frames are about 32 kB or 64 kB respectively. Small sprites are plausible in flash, but full-screen or long animations can consume the application partition quickly.
- The current renderer uses an 8-bit sprite/framebuffer. RGB565, as suggested in the source research, is a candidate output format rather than an automatic choice: it may improve color fidelity but requires checking conversion/blit behavior and code size against the existing RGB332 path.
- No SD-card workflow or other user-accessible image storage is documented for the tested board. Compiling generated assets into firmware is the nearest existing path; external storage would need a separate hardware and configuration decision.

LVGL's published memory estimate makes a useful comparison point, not a measurement of this project's custom player. The actual frame buffer, decoder, transparency, and any intermediate conversion memory must be measured on the target board before selecting a runtime format. [LVGL GIF memory notes](https://github.com/lvgl/lvgl/blob/master/docs/src/widgets/gif.mdx)

## Suggested experiments before choosing an implementation

1. Use a small sample character with a few `idle` and `walk` frames, a static PNG, transparency, and at least one non-uniform frame delay.
2. Convert named PNG frames and one Aseprite export into the same generated representation. Compare color fidelity, flash size, and playback smoothness for RGB332 and RGB565 output.
3. Verify frame order, anchors, trimming, timing, looping, and transparency in a framebuffer capture on the documented display.
4. Record compiled firmware size and free heap during playback. Keep the existing telemetry screens responsive while animation runs.
5. Decide later whether GIF import, packed-sheet import, Lottie/vector effects, external storage, or user-provided runtime assets are worth their extra tooling, memory, and support cost.

## Open questions

- Which source formats should the first converter accept: PNG sequences only, Aseprite files, or both?
- Should generated C/C++ assets be checked into the repo or regenerated as part of the firmware build?
- What upper bounds should be imposed on frame dimensions, frame count, animation count, and total generated bytes?
- Which transparency and palette behavior should be guaranteed on this 8-bit framebuffer?
- Is compiled-in artwork enough, or is removable/external storage a future requirement?

These are implementation questions for a later asset-pipeline task. The current placeholder pages do not require answers.
