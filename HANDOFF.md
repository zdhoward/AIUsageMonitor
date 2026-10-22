# Handoff — 2026-10-22

## Current state

Firmware **v1.4.1** is flashed on the ESP32-2432S024C / COM6. The user accepted the display and asked to wrap up. Latest implementation commit: `9759d32`, tag `v1.4.1`; the wrap-up documentation commit follows it on `main`.

- Landscape rotation **1**, 320×240. Configurable four-way rotation and responsive portrait layout remain available.
- Exactly two tap-cycled views: ring console (default) and original detailed dashboard.
- Console: `AI USAGE (3 CLIENTS)` at left, Session/Weekly column headers aligned over rings. Session (`5h`) left, Weekly (`7d`) right; numbers show exact percent remaining. Weekly is yellow, session uses capacity warning colors. Rings ease toward updated readings.
- Reset countdowns sit beneath each ring. `due` means the deadline passed without a new provider reading; `--` means unavailable. The space below each provider name stays empty for future data.
- Cached readings stay visible at full brightness through stale/missing data. Valid zeros replace cached measurements. Cache is RAM only and resets on power loss. Stale/source status remains visible.
- `config.h` controls rotation, brightness, warning thresholds and animation. Rendering and extension points: [docs/UI.md](docs/UI.md) and [docs/UI_HANDOFF.md](docs/UI_HANDOFF.md).

## Running service and tools

The existing Python service runs hidden, autostarts at logon, and serves `127.0.0.1:8797`. USB serial sends/acknowledges payloads normally; wrap-up health showed v1.4.1, `rot=1 w=320 h=240`, no source errors, port unpaused.

- `scripts/service.ps1 start|stop|restart|status|install|uninstall`
- `scripts/build.ps1` compiles into `build/`; `scripts/flash.ps1` coordinates port release/resume.
- `scripts/screenshot.py --feed --out build/shot.png`; `--next 1` cycles a view before capture, `--rot N` temporarily changes rotation, `--wait N` delays capture.
- Logs: `logs/aimon.log`. Current framebuffer evidence: [docs/img/v1.4.1-rings.png](docs/img/v1.4.1-rings.png).

Quota/reset credits come from T3 caches and newer Codex transcript limits. Token costs are API-price estimates from local transcripts; no credentials or provider quota calls were added. See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

## Validation and repository status

- Latest firmware build passed (413,263 bytes flash, 28,648 bytes static RAM); upload hash verified.
- Framebuffer inspection verified final landscape header alignment, countdown captions, visible empty 0% ring tracks, and empty provider data areas. Serial navigation uses the same action as touch release.
- Wrap-up service suite: **22 tests passed**. Reused the latest green firmware build/capture for documentation-only wrap-up. Details/history: [docs/TEST_REPORT.md](docs/TEST_REPORT.md).
- No open repository PRs and no PRs linked to this thread; nothing needed merging.
- Local commits/tags remain **unpushed**. After the wrap-up commit, `main` is 15 commits ahead of fetched `origin/main`. No remote publication was requested.
- Delegated checkout branches retain partial/superseded worker edits, preserved rather than deleted. They are not extra deliverables. No child task remains active.

## Remaining work

No implementation task is pending. If more data is wanted later, use the intentionally empty provider area; preserve [GOALS.md](GOALS.md). Physical unplug/replug, PC sleep and actual logon-task execution remain unobserved; optional Wi-Fi and cost-estimate reconciliation remain outside scope. Final portrait ring-heading changes were built but not captured on hardware; landscape is the accepted target.

## Routing / next agent

Plan with Sol 6.1 at standard speed; delegate bounded implementation through model-router to available free/local workers. DeepSeek completed T-002/003/004; Beam reviewed early changes, then exhausted free quota. Later `litellm/free-coder` returned intention-only or partial work twice, Qwen timed out, and a later GPT-OSS review never responded. Parent completed small renderer fixes and inspected hardware output; no independent pass is claimed for those later changes. Treat the failing route as unavailable until repaired/rechecked, and verify behavior rather than trusting terminal status. See router lessons and the wrap-up retro log.

Wrap-up added the repeated-incomplete-result rule to shared model-router step 6, updated its lessons, and wrote `C:/Users/ZECHS/.agents/retro/LOG.md`. `sync-instances` reports in sync. The model-router repository already contains other session changes in configuration, skill, lessons and scoreboard; those shared edits were preserved uncommitted rather than mixed into this project's commit. No pending policy approval or model promotion.
