# Handoff — quota correction and idle timing (2026-10-27)

## Current session: T-022 installed, Argon collection still open

- Main commits: `d28df0a` ticket, `0f76d89` 60-second default idle, `123cf9b` direct Gemini quota and pinned layout, `82d56bd` white weekly countdown below 24 hours. No open PRs (`gh pr list` returned none). No public push: GOALS requires owner publication approval. No new release tag/version; installed firmware still identifies as 1.12.0 while exact Argon work is incomplete.
- Root cause: T3's Antigravity cache reports Claude/GPT shared 3p quota. Direct read-only Google fetchAvailableModels now supplies Gemini quota using the existing T3 login; no credential/state files modified. Five-minute polling, bounded requests, in-memory token, original measurement time retained on failures. No weeklyQuotaInfo is currently returned, so weekly is unknown rather than borrowing 3p data. See service/aimon/sources/antigravity.py and docs/DATA_SOURCES.md.
- Display: A/Codex/Antigrav top, B/blank/Argon bottom. Argon is a real separate card but unknown: gemini-4-argon is absent from this token's model list. Do not substitute family quota or infer current quota from 429 logs. Exact agy gateway/quota source is the next research task; previous read-only cloudcode probes did not expose it.
- Default Console/Details idle delay is now 60 seconds; firmware fallback also 60 seconds. Grid weekly reset countdown turns white only for a known future reset below 86400 seconds; at/above a day, unknown, and due remain muted. Weekly rings and percentages keep existing colours.
- Production evidence: Default builds passed, COM6 flash hash verified, main service restarted and feeds five accounts. Coordinator inspected build/t022-console.png and build/weekly-white-live.png. Final build: 584055 bytes flash / 88608 bytes static RAM; logs build/weekly-white-build.log and build/weekly-white-flash.log. Live weekly deadlines exceed one day: highlighted state is not visually verified. Timed 60-second transition, portrait, Rows/Studio, and broader pending acceptance remain unverified. Automated tests NOT run: wrap-up does not declare sprint end under owner policy.
- Source review: Beam PASS; HIGH-risk second free-review unavailable (ECONNREFUSED), not counted as a pass. Coordinator inspected critical logic and separated Argon from family aggregate, cleared retained readings on profile change, bounded cadence/timeouts. Shadow routing capture omitted; paid cost UNKNOWN. No promotion/savings claim.
- Next concrete actions: locate exact agy Argon quota source without model requests; obtain Gemini weekly only if provider actually reports it; owner testing phase should run retained fixtures and verify <24h countdown colour, 60-second saver timing, missing-provider layout, Rows/portrait and existing due-quota saver behavior. Existing unrelated T-016 through T-020 backlog below remains open.
- Efficiency next session: read this section and T-022 first; use narrow source ranges. Record routing shadow before dispatch, and use the existing verifier for source/review evidence; do not reconstruct a large session transcript or treat unavailable review as PASS.

## Previous session (2026-10-26)

## Current session: v1.12.0 compact home

- Delivered on `main`: `3780f9a` adds the optional grid, preserves Rows, enables Default/Grid and includes Gemini/Antigravity T3 quota caches. Wrap-up commit versions this as v1.12.0. No open or thread-linked PRs. Public publication remains subject to the owner's approval rule in GOALS.md; no push in this session.
- Owner refinement: Session/5h uses the larger outer ring for detail; Weekly stays yellow on the inner ring. Both percentages and reset countdowns remain visible. Current live setup is two Claude accounts (A/B), Codex and Antigravity. No local configuration or credentials were replaced.
- Six-account capacity: 3x2 landscape, 2x3 portrait. Only the first six service accounts are stored; no paging. Future providers still need a compatible collector source. Grid uses service display names; stable account IDs remain future work.
- Evidence: successful production builds and hash-verified flashes; `build/t013-final-build.log`, `build/t013-final-flash.log`, `build/console-grid.png`. Coordinator inspected the four-account framebuffer, including 100% next to multi-day captions; owner liked the layout. Final versioned build/flash evidence is `build/v1.12.0-build.log` and `build/v1.12.0-flash.log`.
- Source review: free reviewer found unreachable paging and a calculated text-fit risk. Removed dead paging and corrected docs; actual framebuffer resolves text fit for the current 5h/7d windows. No second independent pass claimed. Automated tests remain deferred under sprint-end policy. Studio selector is wired but click/save/reload and portrait/Rows runtime checks remain pending.
- Tracking: compact-grid ticket is now [T-021](.tickets/T-021.md); dispatch/scoreboard records historically used T-013, already allocated to profiles in the index. Earlier backlog below is retained.
- Next: owner testing phase should cover Rows/Grid save/reload, portrait, six-account/unknown/stale cases and the existing due-quota saver trigger. Then consider explicit overflow handling and provider/account abbreviation configuration. Publication needs owner approval; do not bypass the public push guard. No release tests were implied by this wrap-up.

## Previous handoff: v1.11.1 (2026-10-25)

## Settings review (2026-10-25)

- `docs/SETTINGS_REVIEW.md`: every scene reviewed by local `gemma4:e4b`, checked against `scripts/settings_audit.py`. Only dead controls: sky colours on the 12 generator scenes.
- Follow-ups are [T-020](.tickets/T-020.md). The owner wants each task done in its own session to keep context small.
- Other open items: T-018 owner questions, optional full-history scan of the other public repos, delete the art backup when satisfied, sprint-end tests.

## Latest session: due-quota screensaver suppression

- Implemented and flashed **v1.11.1**, Default profile, COM6. Commit `c5d4858` and tag `v1.11.1` are pushed on `main`; no open PRs.
- `hasDueAvailableUsage` in `firmware/AIUsageMonitor/ui.cpp` checks every reported account/window using the same elapsed reset countdown as the caption. Known usage of 0–99% used with a due reset blocks automatic saving and wakes an active saver, including when usage-change waking is disabled. Unknown values and 100%-used windows do not block it.
- Validation: production build passed (583,159 bytes flash / 87,984 bytes static RAM), upload hash verified, and actual framebuffer captures inspected. `build/screensaver-build.log`, `build/screensaver-flash.log`, `build/screensaver-due.png` and `build/screensaver-dashboard.png` are local evidence. The 31-second capture showed the normal saver; live data had no qualifying due window. The final capture restored Console. These captures do **not** verify the new due trigger.
- Next: at the owner's testing phase, feed a known due window below 100% used and confirm Console/Details remain awake beyond 30 seconds and wake from an active saver. Also check unknown/100%-used exclusions and a deadline crossing. Broader existing acceptance stays open in `docs/SCREENSAVER.md`; automated tests were not run this session.
- Existing scene/audio/stock backlog is unchanged; see the previous session below and `.tickets/README.md`.

## Latest session (v1.8.0 – v1.11.0)

`main` and tags up to `v1.11.0` are **pushed** to the public GitHub repo. The owner wants it public as portfolio work, with code and the system only. Firmware 1.11.0 is flashed on COM6 with the **Default** profile, and the service is running. No open PRs. Details are in [PROJECT_LOG](docs/PROJECT_LOG.md); the owner's decisions are in [GOALS](GOALS.md).

- **Profiles (v1.11.0):** Default (Console → System → Parallax; Console sleeps to the face), Dev (all originals) and Dev (themes) (all theme shifts). Only Console is a required page. Regenerate the scene lists by rerunning the generator logic if the library changes. The Dev profiles list scenes explicitly, so new scenes must be added to them.
- **Random weather (v1.11.0):** `"weather": "random"` on a playlist (`withWeather` in `ui.cpp`, Studio checkbox in `playlists.js`). Confirmed on the display: Miami Drive got snow.
- **Long-press home:** holding for 0.7 s jumps to the Console (`uiGoHome` in `ui.cpp`, `pollTouch` in `AIUsageMonitor.ino`, `UI_HOME_PAGE`/`UI_HOLD_MS`). The owner confirmed it on the display.
- **Footer:** a link dot (green; amber when no payload for 30 s; red on a source error) plus `Updated <newest reading age>`. A stale account is shown only by its card's `STALE` label (60 min, `limits_stale_s` / `CLIENT_STALE_S`). T3 re-polls Claude quota only every few minutes; the serial link is healthy.
- **Account names:** unmatched names (the owner's T3 `A`/`B`) fill the Claude rows in order (`slotIndex`).
- **SVG (v1.9.0):** `asset_convert.py` rasterizes SVGs with `resvg-py` (`pip install resvg-py`). The Images page rotates `"image": true` manifest entries every 10 s. The owner's logo is the test case.
- **Studio UX (v1.10.0):** unsaved chip, ↑/↓ reorder, focus outlines, theme badges, library counts, auto-capture. The "display" wording is now consistent.
- **Validation:** builds at 44% flash, with display screenshots after each flash and Playwright checks of the Studio (the T3 preview snapshot times out, so use Playwright with Edge). No automated tests were run (sprint-end rule).
- **Public repo hygiene (owner rule):** no art, no personal data.
  - Art is local and git-ignored: the owner's GIF, logo, scene `src/` and previews, `assets/manifest.json`, and the generated `assets_gen.*` / `scenes_gen.*`. A clean clone builds at 33% flash: missing art is skipped, and the Images and City pages show hints.
  - The owner's location lives only in the ignored `service/aimon.config.json`; the code defaults are a Greenwich placeholder.
  - Before the first push, the 74 unpushed commits were rewritten with `git-filter-repo` (`python -m git_filter_repo`) in a scratch clone to drop art and scrub paths, username, email and location. They were then pushed as a fast-forward with no force.
  - Backup of the pre-rewrite state: the sibling folder `AIUsageMonitor-art-backup-20261025/` next to the repo (art, generated files and a git bundle). Delete it once satisfied.
- **Before each push:** scan the outgoing diff for personal paths, location, emails, keys and new art.
- **Blockers:** tests are pending sprint end.
- **Next:** hold-progress feedback (optional); a stable slot id per account from the service; flash-size gate; T-017, T-016, T-018 (audio visualizer plan, owner questions open) and T-019 (stock ticker idea).

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
