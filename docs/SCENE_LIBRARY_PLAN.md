# Scene library and Scene Studio plan

**Status:** plan, 2026-10-24. Nothing here is implemented yet except the first scene (`synthwave-city`, commit `ec85856`).

## Goals

1. A **library** of living pixel scenes. Each scene is a folder containing its art, a scene description and license information. Today's synthwave city becomes its first entry.
2. A **generic scene engine** in the firmware, so a new scene is mostly data rather than new C++ code like `city.cpp`.
3. **Profiles**: named build configurations that choose which scenes, pages and settings go onto the device. The flash cannot hold the whole library at once.
4. **Scene Studio**: a small Windows app to browse the library, preview scenes exactly as the device renders them, edit profiles, and build, flash and debug.

## What the downloaded packs need from the engine

The survey of `assets/sprites/` (kept local and ignored by git) shows what the engine has to handle:

| Pack | Shape | Engine need |
|---|---|---|
| Miami-synth (`.ase`), SynthCities, Urban Nightscape 320×180, Dead City 640×360, City Landscape, cyberpunk-street (`.ase`) | Parallax layers, often wider than the screen | **Horizontally scrolling layers** that wrap, each at its own speed; scale/crop to 320×240 |
| Waterfalls 1/2 | 192×192 animated GIFs (8 frames) | Frame animation (already supported); possibly tiled |
| Rain effect (`.aseprite`) | Overlay strip | Animated overlay that tiles across the screen |
| Space Backgrounds | 1280×720 and larger | **Downscale on import** (with a crop or fit choice) |
| pixelmojis (CC0), PixelPatterns | Small sprites and tiles | Sprite props and tiled fills |

Most packs are drawn for 16:9 screens, and the display is 4:3. The importer needs a fit mode for each layer: `cover` (crop) or `fit-height` (scroll the extra width).

## Library layout

```text
assets/library/
  synthwave-city/
    scene.json        # layers, effects, timing, credits
    *.aseprite        # editable art (only if its license allows redistribution)
    preview.png       # device-accurate thumbnail
  miami-drive/        # art kept local when the license forbids redistribution
    scene.json        # points at assets/sprites/... and records the license
```

The fields `scene.json` will probably need are listed below. They get settled in ticket T-012.

- `layers[]`: `src`, `layer`, `kind` (`static` | `anim` | `parallax` | `tile` | `rects`), `x`, `y`, `speed_px_s`, `tag`, `fit`, `flip`.
- `effects[]`: reusable code effects with parameters: `sky_gradient`, `stars`, `synth_sun`, `neon_grid`, `rain`, `lightning`, `window_blink`, `traffic`. These come out of today's `city.cpp`.
- `credits`: author, source URL and license, plus whether the art may be committed to this public repo.
- `budget`: maximum flash bytes and target frame time.

## Profiles

`profiles/<name>.json` holds the scenes to include, the screensaver scene or playlist with its rotation interval, page enables, timeouts, rotation and brightness settings. The converter and `build.ps1 -Profile <name>` turn a profile into generated config overrides plus scene data. A profile fails to build if it exceeds its flash budget. Measured: roughly 800 KB of the partition remains free for assets.

## Scene Studio (Windows app)

**Recommended stack:** a Python + PySide6 desktop app. The repo's tooling (service, converter, screenshot) is already Python, and serial, subprocess and image handling come easily.

**Exact preview:** compile the firmware's own `anim.cpp` and scene engine as a small Windows DLL (`Canvas8` has no TFT dependency) and call it from the app. The preview then matches the device pixel for pixel, including RGB332 banding. Emulating the renderer in Python would drift from the firmware.

Panels:

1. **Library**: thumbnails, license and redistribution status, flash bytes and estimated frame time for each scene.
2. **Preview**: live emulated playback at device size with a speed control, layer toggles and frame stepping. Side by side, a **device mirror** captured over `!SHOT`.
3. **Import**: drop in a GIF, PNG or Aseprite file to see the RGB332-quantized result, encoded bytes and fit/crop choice, then add it to a scene.
4. **Profiles**: edit the scene selection and settings, with a live flash-budget bar.
5. **Device**: build, flash, serial console (`!PERF`, `!NEXT`, `!FACE`), live FPS/heap graph, and screenshot capture.

The Studio has to share the COM port with the running aimon service the same way `flash.ps1` and `screenshot.py` do (the service's `/v1/serial/pause` API).

## Tickets (tracer-bullet order)

- **T-012 Scene library and engine**: move the city into `assets/library/synthwave-city/scene.json`; implement the generic engine with parallax/tile layers and extract the effects; rebuild the city on top of it with no visual change (checked with a framebuffer diff); add one imported pack scene (Miami-synth) as proof.
- **T-013 Profiles**: profile schema, `build.ps1 -Profile`, flash budget enforcement, screensaver scene playlist.
- **T-014 Scene Studio MVP**: host DLL preview, Library and Preview panels, and the Device panel (build/flash/shot/PERF).
- **T-015 Studio editing**: Import panel, profile editor, layer toggles, frame stepping.

## Open decisions

- Licenses: Miami-synth and cyberpunk-street (Ansimuz) and pixelmojis are CC0, verified from their bundled license files, so they may be committed. City, City Landscape, Dead City, Urban Nightscape, SynthCities, Rain effect, Waterfalls, Space Backgrounds and PixelPatterns have no bundled license; check each one's itch.io page before committing any of their art. Until then they stay local and are referenced by path.
- `assets/gif/angry_skele.gif` is committed locally (`ec85856`, not pushed) with an unknown license. Confirm it may be published before pushing.
- Whether the screensaver should rotate through several scenes or show one per profile.
