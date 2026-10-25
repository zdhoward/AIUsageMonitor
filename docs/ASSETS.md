# Images, GIFs and animated scenes

Artwork is converted on the PC and compiled into the firmware. The ESP32 only plays frames back.

## Pipeline

```text
assets/<gif|png|aseprite>  --(assets/manifest.json)-->  scripts/asset_convert.py
   --> firmware/AIUsageMonitor/assets_gen.{h,cpp}  (RLE RGB332, committed)
   --> anim.cpp player  --> Images page / City page
```

**Art is yours and stays local.** The repo ships the code and the system, not images. `assets/manifest.json`, `assets/gif|img|scenes/`, each library scene's `src/` and `preview.png`, and the generated `assets_gen.*` / `scenes_gen.*` are git-ignored. A fresh clone builds anyway:
- missing manifest entries and scenes whose art is absent are skipped;
- the Images and City pages show a hint;
- procedural scenes (plasma, fire, aurora…) work out of the box.

`scripts/build.ps1` regenerates the art tables on every build.

1. Put the source file under `assets/` and add an entry to `assets/manifest.json`. Copy `assets/manifest.example.json` to start it.
2. Run `python scripts/asset_convert.py`. It prints the encoded size of each asset.
3. Build and flash: `scripts/build.ps1`, then `scripts/flash.ps1`.

Supported sources:

| Source | Notes |
|---|---|
| `.gif` | All frames, with each frame's own delay. |
| `.png` / `.jpg` | One still frame. |
| `.aseprite` / `.ase` | Exported through the Aseprite CLI. Frame durations and tags are kept. Set `layer` to export a single layer. |
| `.svg` | One still frame, rasterized with `resvg-py` (`pip install resvg-py`) to fit `size` (default 300x210, aspect kept). Needs a `viewBox`. Set `bg` to the page colour (`#000000` on the Images page) so anti-aliased edges blend instead of being cut. Example: `img/grid_logo_1_light.svg`. |

Manifest fields: `name`, `src`, optional `layer`, optional `mode: "rects"`, optional `max_bytes` budget, optional `image: true` (shown on the Images page, which rotates through these in manifest order every `UI_IMAGE_SECONDS`, default 10), and the SVG options `size` and `bg`. `rects` mode outputs the bounding box and colour of each separate blob in the first frame instead of image data. The city's blinking windows use it.

Colours are snapped to RGB332 (8 red, 8 green and 4 blue levels). Pixels with alpha below 128 are transparent. Frames are trimmed to the opaque area they share, so an Aseprite layer keeps its position on the canvas.

## City scene

The art lives in `assets/scenes/city/`:

- `city.aseprite`, 320×240, with layers `far` (distant skyline), `near` (foreground towers) and `windows` (each lit window is its own blob).
- `sign.aseprite`, the neon "AI" sign, tag `flicker`.
- `car.aseprite`, the hover car, tag `fly`; it faces right and the code flips it for the other direction.

Edit these in Aseprite, then run the converter. `scripts/gen_city_art.py` created the first version. It refuses to overwrite your edits without `--force`.

`city.cpp` draws the moving parts: sky gradient and stars, the striped synthwave sun, the scrolling neon grid and wet-road reflection, rain with splashes, window blinking, lightning flashes, and traffic. The positions of the sign and cars are constants in `cityDraw`.

## Measured on the board (2026-10-24)

- City page: 54 ms per frame including the panel transfer (about 18 fps). Free heap during playback is 238 KB. Use `!PERF` over serial to check.
- All current assets take about 21 KB of flash; the firmware is 444 KB of the 1,280 KB partition.
- A full-screen 8-bit frame costs at least 31 ms on the SPI bus alone, so roughly 20 fps is the ceiling for full-scene animation.

Pages: `UI_IMAGE_ENABLED` and `UI_CITY_ENABLED` in `config.h`. To use the city as the screensaver, set `UI_SCREENSAVER_PAGE` to `UI_PAGE_CITY`.

## Scene Studio

Double-click `Scene Studio.cmd` in the repo root (or run `python -m studio`). It opens an app window at http://127.0.0.1:8798 with four tabs:

- **Layout**: drag pages into tap order, switch optional pages on or off, set orientation and whether quota numbers show remaining or used.
- **Screensaver**: on/off, which scene to show, how soon it starts, and per-page sleep and wake rules.
- **Library**: everything saved so far (`assets/library/<name>/entry.json` + `preview.png`). Each entry records the profile and git commit that produced it.
- **Display**: capture the live screen, step through pages, see frame time, FPS and free memory, and save a capture to the library.

Profiles live in `profiles/<name>.json`. **Send to display** saves the profile, converts art, builds with `build.ps1 -Profile <name>` (which writes the git-ignored `profile_gen.h`) and flashes. The `+` button next to the profile list duplicates the current profile. The server only listens on localhost and only needs the Python standard library plus pyserial.

The screensaver timer restarts whenever measured usage changes, so it will not start while agents are actively using quota.

## Parallax scenes (scene engine)

Any library entry with `"kind": "scene"` becomes part of the **Scene playlist** page, which loops through scenes Roku-style, `scene_seconds` each (profile setting, default 90). The schema is documented at the top of `scripts/scenes.py`. In short:

- `layers` (back to front): `src` (png/gif/aseprite, or a list of frames), `speed` px/s, `y`, `scale`, `gap`, `ms`. Layers wrap forever; a speed of 0 means still and centred.
- `effects`: `stars`, `rain`, `snow`, `lightning`, each with density 1-3 and a colour.
- `theme` plus `variants`: palette remaps applied on the device (vapor, toxic, dusk, ice, matrix, amber, noir, night, sunset). Variants reuse the same art, so each one costs 256 bytes.
- Soft alpha (glows) is blended over the sky gradient during conversion.

Current scenes: Miami Drive, Neon Skyline and Rainy Street, all CC0 by Ansimuz, plus their theme variants. Together they take about 113 KB; the firmware is 562 KB, 42% of the partition. Measured 56-66 ms per frame on the board.

Serial: `!SHOW <page|scene-id>` shows any page or scene until the next tap, even one not in the tap rotation; `!SCENES` lists compiled scene ids. Every page is now compiled in, and the profile's page list only sets the tap rotation.

### In the Studio

- **Library → click any card** to open the viewer. Pages and scenes have **Show on display**. Scenes play a live preview in device colours and can be edited: themes and playlist variants, layer speeds, effects, sky. **Save scene**, then **Send to display**.
- **Import art**: drop PNG/GIF/JPG/Aseprite files, ordered back to front. Several files, or one Aseprite file with layers, become a parallax scene with depth-based speeds from 4 to 60 px/s and a sky sampled from the back layer. A single image becomes a still scene.
- Imported art is copied to `assets/library/<id>/src/` and committed with the library. **The repo is public**: import only art whose license allows redistribution, and record it in the License field.

### Generators and per-card settings

- `generator` in a scene replaces the sky with a procedural backdrop: `patterns` (1-bit 16x16 tiles in colour pairs, drifting, wiping to the next every few seconds), `plasma`, and `warp` (starfield). See `scripts/scenes.py`. Measured 46-52 ms per frame.
- Every library card has a **gear** that opens its settings. Scenes: layer speed, frame time (for example the Miami car, now 160 ms over 4 frames), gap, and fit for still pictures (original, pixel, contain, cover, stretch). Generators: zoom, drift, timing and colours. Console/Details: quota ring colours for the active profile; the weekly ring can use the session thresholds instead of yellow.

### Playlists and Digital Rain

- **Playlists tab**: build any number of named rotations (up to 16). Pick scenes, drag them into order and set seconds per scene. Each playlist can be a tap page (`playlist:<id>` in the profile's `pages`) or the screensaver. The built-in **All scenes** page rotates through everything every `scene_seconds`. `!SHOW playlist-<n>` plays playlist n (profile order) on the display; the tab's **Show on display** button sends this. **Random weather** (`"weather": "random"` on a playlist) gives each scene turn clear skies, rain, snow or a storm, replacing the scene's own rain/snow/lightning and keeping its stars (`withWeather` in `ui.cpp`).
- Firmware: playlist pages are ids 200 and up; `scripts/profile_gen.py` writes their scene lists to the git-ignored `playlists_gen.h`.
- **Digital Rain** (`matrix` generator): an original take on the effect in Rezmason/matrix, with no code or font copied. Glyphs are generated from a hash, columns fall with a white head and a fading trail, and characters flicker. Settings: glyph size, fall speed, density %, colours (background, trail stops, head). About 43 ms per frame on the board.

### Theme cycles and Lospec palettes

- **Smooth theme cycle**: in a scene's Theme section, switch "Ticked themes" to *smooth cycle*. The scene then holds each ticked theme for `hold` seconds and cross-fades to the next over `fade` seconds (`"cycle": {"themes": [...], "hold": 20, "fade": 4}` in the scene). On the device, the two palette maps are blended each frame (256 entries). Fades step through RGB332's 8 red, 8 green and 4 blue levels, so they are smooth but slightly stepped. *Playlist copies* mode keeps the old behaviour: each ticked theme becomes its own playlist entry.
- **Lospec palettes**: "Browse Lospec palettes" searches [lospec.com](https://lospec.com/palette-list) by tag (through `/api/lospec`), or takes a pasted palette link. Added palettes are saved to `assets/themes/<slug>.json` with name, author and link, and become themes that map colours by brightness onto the palette's own colours. Neon Pulse 8 (by pablokld) is included.
- Demo: Neon Skyline cycles original, Neon Pulse 8 and dusk (10 s hold, 4 s fade). Captured on COM6.

### Native preview, live device tuning and simulation effects (2026-10-25)

- **Native preview**: `studio/native/build.ps1` compiles the firmware scene engine (`scene.cpp`, `anim.cpp`, `tune.cpp`, generated `scenes_gen.cpp`) with MSVC into `studio/native/build/scenehost-<stamp>.dll`. The Studio streams frames from it (about 48 fps), so previews are the device's own pixels, and new effects only need writing once, in C++. The Studio rebuilds it when the library changes, after imports and after each Send to display. Scenes not yet in the engine fall back to the JavaScript preview.
- **Tune blobs** (`firmware/AIUsageMonitor/tune.h`): a compact binary override of a compiled scene's sky, layer speeds/positions, effects, theme, generator settings and theme cycle. The preview applies unsaved edits through it, and **Live on device** in the scene viewer sends it to the display as `!TUNE <hex>` (`!TUNE off` clears it). Art changes (import, fit) still need a Save, then Send to display.
- **Lightning** now fills the whole screen with its colour behind layer `behind` (default 1, in front of the back layer only), so buildings stay crisp in front of the flash.
- **Theme list**: a filterable list with Main (radio), Copy or Cycle (tick), cycle order (↑↓) and removal of imported palettes.
- **New generators** (original implementations; credits in each library entry): `fire`, `lava` (metaballs), `aurora`, `life`, `ripple`, `fireworks` (inspired by termflix and sysc-Go, both MIT), `videoeq` (bitwise video equations, after the Video EQ synthesiser) and `spectre` (oscillators, shape and comparator patched through logic into 8 colours, after the EMS Spectre / open_spectre). They share a 38 KB scratch buffer and take `scale`, `speed`, `density` or `mode`, `seconds` and `colors`.
