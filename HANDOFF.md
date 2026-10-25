# Handoff — v1.5.0 Scene Studio and scene engine (2026-10-25)

## State

`main` is tagged `v1.5.0` (local only; not pushed). The firmware reports 1.5.0 and is flashed on COM6 with the Default profile. No open PRs.

Delivered this session (details in [ASSETS](docs/ASSETS.md), [plan](docs/SCENE_LIBRARY_PLAN.md), [project log](docs/PROJECT_LOG.md)):

- **Assets:** `scripts/asset_convert.py` converts GIF/PNG/Aseprite to RLE RGB332. `anim.cpp` is the player. The Images page plays a GIF; the City page is `city.cpp`.
- **Scene engine:** `scene.cpp`, built from `scripts/scenes.py`:
  - parallax layers, effects (stars, rain, snow, lightning behind layer N), themes, theme variants and smooth theme cycles;
  - Lospec palette themes in `assets/themes/`;
  - generators: patterns, plasma, warp, matrix, fire, lava, aurora, life, ripple, fireworks, videoeq, spectre.
- **Pages:** every page is compiled in. A profile chooses the tap order, `scene:<id>` pages, up to 16 playlists (`playlist:<id>`, firmware ids 200+), the screensaver target and ring colours. Generated files: `profile_gen.h` and `playlists_gen.h` (both git-ignored).
- **Serial commands:** `!SHOW <page|scene|playlist-n>`, `!SCENES`, `!PERF`, `!TUNE <hex>|off`. The tune format is in `firmware/AIUsageMonitor/tune.h`.
- **Scene Studio** (`Scene Studio.cmd` or `python -m studio`; test instances use `--port 8799`):
  - tabs: Layout, Screensaver, Playlists, Library (gear settings, import, Lospec browser), Display;
  - previews come from the native DLL (`studio/native/build.ps1`, MSVC), at about 48 fps;
  - **Live on device** sends unsaved edits to the display.
- **Library:** 23 entries in `assets/library/`.

## Measured

- Flash use is 574 KB (43%). Static RAM is 85 KB; 184 KB heap is free during scenes.
- Scenes run at 43-68 ms per frame on the device.
- The native preview renders a frame in under 0.2 ms.

## Not done / blockers

- Automated tests: none run (owner's sprint-end rule). The service suite is `python -m unittest discover -s tests -t .` from `service/`.
- Never observed on the device: the screensaver taking over by itself (active usage keeps waking it).
- Untested: portrait rotation for scenes.
- No flash-budget gate in the build.
- `assets/gif/angry_skele.gif` has an unknown license. Confirm it before any push; the repo is public.
- Third-party packs in `assets/sprites/` are git-ignored. Only CC0 art is committed.

## Next actions

1. T-017: VJ transitions between playlist scenes, plus more effects (boids, radar, reaction-diffusion; cracktro, beams).
2. T-016: classic screensavers (3D Pipes, Maze, Mystify) as generators.
3. Port `city.cpp` onto the scene engine so the city can be edited in the Studio.
4. Add a flash-budget check to `build.ps1 -Profile`.

## Commands

- Build/flash: `scripts/build.ps1 -Profile default`, then `scripts/flash.ps1`. Convert art first with `python scripts/asset_convert.py --profile default`.
- Native preview: `powershell -File studio/native/build.ps1`.
- Capture: `python scripts/screenshot.py --out shot.png`, or the Studio's Display tab.
- Keep sessions short: this one reached a 612k-token context (see the retro in `~/.agents/retro/LOG.md`).
