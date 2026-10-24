# Handoff — MINT implementation complete, visual pages continue (2026-10-23)

Current continuation: T-010 implements automatic 30-second idle saving and
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

## Next task: image and GIF display

The owner explicitly wants to tackle image and GIF display next. Start by inspecting the existing Images page, asset research, and the untracked `assets/` directory (currently contains `gif/`, `img/`, and `vid/` folders; preserve user contents). Continue from the current main commit; keep MINT and the quota console intact. Use T-008K and the measured-renderer constraints as planning context, but deliver the user's requested image/GIF slice directly. Record supported source formats, conversion workflow, frame memory/transfer budget and playback behavior before adding dependencies or larger assets. Device performance has not yet been baselined under sustained MINT; keep animation bounded and measure a representative small image/GIF on the board. No new request for repository publication has been made.

Other T-008 follow-up remains open: automatic Screensaver activation/wake semantics and renderer/transport measurement (B/C), plus optional procedural scenes (G–J). T-008 image/GIF work is K. Physical taps for the earlier T-008A page navigation also remain unverified. See [T-008](.tickets/T-008.md), [MINT](docs/MINT.md), [test report](docs/TEST_REPORT.md), and [project log](docs/PROJECT_LOG.md).

## Verification and commands

- Production build passed after the final source change; build size above. Existing `TOUCH_CS` warning is expected for this board.
- Python syntax compilation and `git diff --check` passed in implementation workers; focused service tests and firmware fixtures are retained but unrun.
- Device state at handoff: aimon service healthy on COM6, firmware `1.4.2 rot=1 w=320 h=240 fb=1`, serial ACKs resumed. Screenshot helpers coordinate pause/resume.
- Build: `powershell -NoProfile -File scripts/build.ps1`; flash: `powershell -NoProfile -File scripts/flash.ps1 -Port COM6`; capture: `python scripts/screenshot.py --port COM6 --feed --out docs/img/capture.png`.
- Sprint-end service suite: from `service/`, `python -m unittest discover -s tests -t .`. Follow the owner’s sprint-end testing rule.
- Worktree has a pre-existing untracked `assets/` directory with `gif/`, `img/`, `vid/`; inspect and preserve it. Ignore build logs are under ignored `build/`.
- This wrap did not fetch, push, tag or inspect/merge PRs. Local `main` has unpushed commits; verify remote freshness before any publication. No PRs were created or worked on.
