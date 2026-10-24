# Handoff — MINT implementation complete, visual pages continue (2026-10-23)

Latest installation (2026-10-24): T-011 automatic brightness is installed on COM6 (420,143 bytes flash / 29,808 bytes static RAM). Main service resumed ACKs and reports the owner's city night duty 40/255, 1000ms interpolation, nine cached dates and no brightness errors. See [brightness configuration](docs/BRIGHTNESS.md) and `.tickets/T-011.md`; evidence is under ignored `build/t011-*`. Firmware still reports development baseline 1.4.2; no new release tag. Automated tests, physical calibration and broader acceptance remain pending. Older build sizes below predate T-011.

Previous continuation: T-010 implements automatic 30-second idle saving and
usage-change wake for Console/Details, with separate per-view settings.
Face/Images are exempt; Screensaver is removed from navigation. Built at
419,663 bytes flash / 29,760 bytes static RAM and flashed to COM6 with hash
verification; service ACKs resumed. See [screensaver acceptance](docs/SCREENSAVER.md)
and [T-010](.tickets/T-010.md). Automated tests remain deferred. The earlier
T-008A five-entry navigation and saver-unimplemented statements below are history.

## Current state

The Grobot-powered MINT face and PC-owned behavior are integrated on local `main`. Main commits for this work: `d46c8c3` (face), `d8c81f6` (service behavior), `1ea6046` (restart/expiry fixes), `bc50a81` (mouth canvas path), `7fead74` (unsigned blend fix), `0d6dd47` (wrap-up evidence/docs). The face has seven table-driven expressions, independent blink/gaze/mouth/sweat animation, smooth target blending and the upstream MIT notice. Service behavior provides gradual mood, finite local pet/play/nap reactions and optional default-off Windows CPU/RAM stress. The existing service remains the sole serial owner.

Current firmware was built at **418,663 bytes flash / 29,000 bytes static RAM**, flashed to COM6 with hash verification and reports rotation 1, 320×240, framebuffer enabled. Service restarted and serial ACKs resumed. Actual captures inspected by the coordinator: [happy](docs/img/MINT-happy-device.png), [idle](docs/img/MINT-idle-device.png). They show eyes and mouth across the face, without a body or page chrome. The initial missing-mouth discovery and unsigned-time fix are recorded in the project log; do not use older worker screenshots.

Code review passed for the main face and PC behavior, including corrective review for durable ordered service sessions and permanent lease expiry. No service tests or firmware fixtures were executed; owner sprint-end policy defers them. Still pending: sustained animation/latency and heap measurement, all emotion appearances, physical touch, portrait, direct-panel allocation fallback, reconnect/expiry fixture driver, and real optional CPU/RAM sampling. Still captures pause serial and are not FPS evidence. Development binary continues to report firmware version 1.4.2; identify it by source/artifact SHA, not that version string. No release version/tag, remote push or PR work occurred.

## Current state (2026-10-24): image/GIF playback, synthwave city and Scene Studio

Delivered: converter (`scripts/asset_convert.py`), frame player (`anim.cpp`), Images page plays `angry_skele.gif`, City page (`city.cpp` + `assets/scenes/city/*.aseprite`), `!PERF`, configurable page order (`UI_VIEW_ORDER`), build profiles (`profiles/*.json`, `build.ps1 -Profile`), and Scene Studio (`python -m studio`, `Scene Studio.cmd`). Flashed on COM6 with the default profile, screensaver set to City. Measured 42-54 ms/frame, about 232-238 KB of free heap. See [ASSETS](docs/ASSETS.md) and [scene library plan](docs/SCENE_LIBRARY_PLAN.md).

Next: T-012 generic scene engine (parallax/tile layers) with Miami-synth (CC0) as the first imported pack; then Studio live preview through a host DLL. Third-party packs in `assets/sprites/` are git-ignored because the repo is public; `angry_skele.gif` has an unknown license, so confirm before pushing. City-as-screensaver was not observed on the device because live usage changes kept waking it; recheck when idle.

## Verification and commands

- Production build passed after the final source change; build size above. Existing `TOUCH_CS` warning is expected for this board.
- Python syntax compilation and `git diff --check` passed in implementation workers; focused service tests and firmware fixtures are retained but unrun.
- Device state at handoff: aimon service healthy on COM6, firmware `1.4.2 rot=1 w=320 h=240 fb=1`, serial ACKs resumed. Screenshot helpers coordinate pause/resume.
- Build: `powershell -NoProfile -File scripts/build.ps1`; flash: `powershell -NoProfile -File scripts/flash.ps1 -Port COM6`; capture: `python scripts/screenshot.py --port COM6 --feed --out docs/img/capture.png`.
- Sprint-end service suite: from `service/`, `python -m unittest discover -s tests -t .`. Follow the owner’s sprint-end testing rule.
- Worktree has a pre-existing untracked `assets/` directory with `gif/`, `img/`, `vid/`; inspect and preserve it. Ignore build logs are under ignored `build/`.
- Wrap-up status 2026-10-23: `main` at `8031fa9` (handoff reconciliation), 32 commits ahead of `origin/main`; not fetched or pushed. No release tag. `gh pr list --state open` and T3 linked-PR list were empty, so no PRs needed merging. Preserve untracked `assets/gif`, `assets/img`, and `assets/vid`. Automated tests were not run; see sprint-end checklist.
