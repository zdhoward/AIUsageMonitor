# Handoff — v1.9.0 Long-press home, reliable link status, SVG images (2026-10-25)

## Latest session (v1.8.0)

`main` is tagged `v1.10.0` (local only; not pushed). Firmware 1.9.0 is flashed on COM6, and the service was restarted with the new stale threshold. No open PRs. Details are in [PROJECT_LOG](docs/PROJECT_LOG.md).

- **Long-press home:** holding for 0.7 s jumps to the AI Usage console (`uiGoHome` in `ui.cpp`, hold detection in `pollTouch` in `AIUsageMonitor.ino`, `UI_HOME_PAGE`/`UI_HOLD_MS` in `config.h`). The owner confirmed it on the device.
- **Footer:** a green/amber/red link dot plus `Updated <newest reading age>`. Amber means no payload for 30 s and red means a source error. Old readings on one account show only as that card's `STALE` label (threshold 60 min, `limits_stale_s` / `CLIENT_STALE_S`).
- **Why the link looked unreliable:** T3 refreshes Claude quota only every few minutes, so an idle account's reading ages on its own. The serial link itself is healthy.
- **Account names:** the owner renamed the T3 Claude instances to `A`/`B`. Unmatched names now fill the Claude rows in order (`slotIndex`).
- **Profile:** the default profile with 12 single-scene pages (19 pages total) is committed.
- **Validation:** builds at 44% flash, and device screenshots were checked after each flash. No automated tests were run (sprint-end rule).
- **SVG (v1.9.0):** the owner's logo `assets/img/grid_logo_1_light.svg` is the SVG test case. `asset_convert.py` rasterizes SVGs with `resvg-py` (a new tool dependency: `pip install resvg-py`). The Images page rotates through `"image": true` manifest entries every 10 s. See [ASSETS](docs/ASSETS.md).
- **Studio UX pass (v1.10.0, Studio only):** see the project log. Deferred: grouping the Layout page list, and one term for display/device.
- **Next:** optional hold-progress feedback. To clean up the row-mapping heuristic, the service could send a stable slot id per account.

## Previous session (v1.6.0)

`main` is tagged `v1.6.0` (local only; not pushed). Firmware 1.6.0 is flashed on COM6 with the Default profile. The service is running with the fix. No open PRs.

- **Fix:** the display had stopped updating. A Studio pause cleared the serial handle while the serial thread was writing, and the uncaught error killed that thread silently. `service/aimon/serial_link.py` now uses a local handle and catches everything.
- **System page** (`system`, after Details in the default profile) shows CPU, RAM (used/total), GPU, disk read/write and download/upload. There are no graphs, and values ease on the device.
  - `service/aimon/sysstats.py` samples with psutil, plus GPU from Windows PDH "GPU Engine" counters via ctypes.
  - The sample is sent as a separate 1 Hz `{"t":"sys",...}` line; firmware routes it in `pollSerial` to `parseSys`.
  - The page is `drawSystem` in `ui.cpp`.
- **Validation:** builds at 44% flash, and a device screenshot is in `docs/img/system-page.png`. Smooth motion is not yet confirmed by the owner. No tests were run (sprint-end rule), and no unit test covers the new sampler or the pause race.
- **Next:** confirm the easing feel (the 250 ms constant in `drawSystem`). Optionally add a regression test for pause-during-write in `service/tests`.
- **Page indicator** (`bfbfa92`): up to 6 pages show dots; beyond that `drawDots` shows a "3 / 19" counter over a thin position track. Flashed and captured on the device. Possible follow-up the owner may want: grouping pages into sections (swipe between groups, tap within one).
- **Not mine, left alone:** uncommitted `profiles/default.json` edits from another session (they were included in the last flash, so the device now has 19 pages) and the untracked `assets/img/`.

## Previous session (v1.5.0)

Delivered in v1.5.0 (details in [ASSETS](docs/ASSETS.md), [plan](docs/SCENE_LIBRARY_PLAN.md), [project log](docs/PROJECT_LOG.md)):

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
