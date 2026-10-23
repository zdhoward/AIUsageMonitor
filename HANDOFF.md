# Handoff — visual pages plan, 2026-10-23

## Current session and next action

The owner gathered optional display ideas and asked for a solid implementation plan to be reviewed and enhanced by Sol 6.1 before implementation. The consolidated brief is [T-008](.tickets/T-008.md); it is linked from the README and ticket index. Use the owner's latest Sol review prompt from the conversation, or follow the review request inside T-008. Sol is to update the plan and return bounded implementation tickets; do not treat the planning ticket as authorization to implement.

- T-008 covers page/build configuration, a default-off screensaver, PC-driven MINT, optional procedural starfield/tiny-world/liquid scenes, and a future image/animation pipeline.
- The existing serial connection is owned by the PC service and carries newline-delimited JSON. Do not create a competing bridge process for MINT. MINT behavior belongs on the PC; firmware renders received state.
- Research notes are in [IMAGE_ANIMATION_RESEARCH.md](docs/IMAGE_ANIMATION_RESEARCH.md); they distinguish source sketches from verified runtime behavior and record display/transfer constraints.
- **Baseline needs reconciliation:** the owner reported four views on the flashed device, but this `main` checkout's current firmware documents Console and Details only. Identify the intended implementation branch/commit and inspect the actual device baseline before drafting implementation tickets.
- Local `main` is nine commits ahead of `origin/main`. Those commits are not pushed. Worktree was clean at wrap-up. No open pull requests were found. No tests or firmware build were run for this docs-only planning work; `git diff --check` passed before commit.
- No firmware version bump or tag was made. Keep firmware version distinct from documentation-only commits.

Suggested immediate sequence: Sol 6.1 reviews T-008 read-only, reconciles the code/device discrepancy, splits it into small tickets with dependencies and evidence criteria, then returns unresolved owner questions. After that review, the owner can choose which implementation ticket to start and route it to a suitable Luna/free lane.

## Prior release baseline

The notes below describe the last public-release baseline before the local planning commits; verify against the intended branch before relying on them.

Firmware **v1.4.2** is flashed on the verified ESP32-2432S024C. Implementation commit `315d70c` is tagged `v1.4.2`; later documentation commits do not change the firmware version.

- Landscape rotation 1, 320×240; two tap-cycled views: console and details.
- Three stable rows: Claude A, Claude B, Codex; Session left, Weekly right, percent remaining.
- Bright font 2 reset captions, rings raised 6px. `--` is unknown, `due` is a passed deadline. Measured zero stays distinct.
- Cached readings remain bright; RAM cache resets at reboot. Source age and link health remain visible.
- Collector rereads caches/transcripts at deadlines and normally every 10 seconds. It does not force provider queries or infer refills.

## Public preparation

The owner selected **MIT**, pushed the completed docs, and directed the repository to be made public. GitHub now reports the repository as public, with a project description and topics. `main` was pushed through `a7f2dd7`; no subsequent source changes are pending in the published tree. The docs and current-source secret scan are complete. Earlier Git history includes the board MAC address and local Windows paths described in [PUBLIC_RELEASE.md](docs/PUBLIC_RELEASE.md); no history rewrite was performed.

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

GitHub URL: https://github.com/zdhoward/AIUsageMonitor. At the prior release wrap-up, remote `main` and local `main` were synchronized at `a7f2dd7`; the current local branch has since advanced and is described above. The repository description is “An ESP32 dashboard for AI subscription quotas, reset countdowns, and local usage telemetry.” Topics: `esp32`, `arduino`, `python`, `dashboard`, `embedded`, `usage-monitor`. Preserve unrelated partial worker checkouts.

Documentation routing: hosted free worker hit quota; local fallback was cancelled after producing no edits in the allotted time. Coordinator completed the documentation; no independent model review is claimed. Shadow routing run and validation details are in the project log.
