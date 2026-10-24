# Images, GIFs and animated scenes

Artwork is converted on the PC and compiled into the firmware. The ESP32 only plays frames back.

## Pipeline

```text
assets/<gif|png|aseprite>  --(assets/manifest.json)-->  scripts/asset_convert.py
   --> firmware/AIUsageMonitor/assets_gen.{h,cpp}  (RLE RGB332, committed)
   --> anim.cpp player  --> Images page / City page
```

1. Put the source file under `assets/` and add an entry to `assets/manifest.json`.
2. Run `python scripts/asset_convert.py`. It prints the encoded size of each asset.
3. Build and flash: `scripts/build.ps1`, then `scripts/flash.ps1`.

Supported sources:

| Source | Notes |
|---|---|
| `.gif` | All frames, with each frame's own delay. |
| `.png` / `.jpg` | One still frame. |
| `.aseprite` / `.ase` | Exported through the Aseprite CLI. Frame durations and tags are kept. Set `layer` to export a single layer. |

Manifest fields: `name`, `src`, optional `layer`, optional `mode: "rects"`, optional `max_bytes` budget. `rects` mode outputs the bounding box and colour of each separate blob in the first frame instead of image data. The city's blinking windows use it.

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
