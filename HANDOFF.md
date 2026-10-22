# Handoff — public documentation preparation, 2026-10-22

Firmware **v1.4.2** is flashed on the verified ESP32-2432S024C. Implementation commit `315d70c` is tagged `v1.4.2`; later documentation commits do not change the firmware version.

- Landscape rotation 1, 320×240; two tap-cycled views: console and details.
- Three stable rows: Claude A, Claude B, Codex; Session left, Weekly right, percent remaining.
- Bright font 2 reset captions, rings raised 6px. `--` is unknown, `due` is a passed deadline. Measured zero stays distinct.
- Cached readings remain bright; RAM cache resets at reboot. Source age and link health remain visible.
- Collector rereads caches/transcripts at deadlines and normally every 10 seconds. It does not force provider queries or infer refills.

## Public preparation

The owner chose **MIT** and **prepare locally for review**. Keep GitHub private: no push, visibility change or release without later authorization. Review [PUBLIC_RELEASE.md](docs/PUBLIC_RELEASE.md), especially its history disclosure. Earlier commits contain a board MAC address and local Windows paths; current-file cleanup does not erase history.

The README leads with the [v1.4.2 framebuffer](docs/img/v1.4.2-rings.png). Setup, complete implemented GPIO mapping, data sources, protocol/API and contribution guidance support reproduction. The safe example config disables optional OpenRouter access; the code default is still enabled. Python USB dependency is pinned in `service/requirements.txt`.

## Validation baseline

- 22 service tests pass on unchanged v1.4.2 code.
- Firmware build: 413,263 bytes flash, 28,648 bytes static RAM; upload hash verified.
- Device reports v1.4.2, `rot=1 w=320 h=240 fb=1` and normal acknowledgements. Framebuffer inspected for layout/clearance.
- Physical viewing comfort, tap reliability, unplug/replug, sleep and real logon remain unverified. Optional Wi-Fi is untested.
- Deadline scheduling was inspected, not observed through a real reset or covered by a dedicated timer test.
- Final docs/link/config and secret-scan results: [project log](docs/PROJECT_LOG.md). No fresh board compatibility is claimed.

## Commands and next actions

From the root: `scripts/service.ps1 status`, `scripts/build.ps1`, `scripts/flash.ps1`, and `python scripts/screenshot.py --feed --out build/dashboard.png`. From `service/`: `python -m unittest discover -s tests -t .`. The service binds to localhost port 8797; screenshots/flashing coordinate serial-port release. Logs and builds are Git-ignored.

Owner next reviews README, pinout, screenshot and public-history considerations. After explicit publication authorization, verify remote state and push only intended branch/tags before changing visibility. No PR or remote release was created during preparation. Preserve unrelated partial worker checkouts.

Documentation routing: hosted free worker hit quota; local fallback was cancelled after producing no edits in the allotted time. Coordinator completed the documentation; no independent model review is claimed. Shadow routing run and validation details are in the project log.
