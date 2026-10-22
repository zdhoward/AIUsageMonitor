# Handoff

Current update: **v1.3.1, 2026-10-22** — exactly two tap-cycled views: the new three-client status console and original detailed dashboard. Landscape rotation 1, full-brightness cached readings, labeled urgent quota/reset timing, source freshness, eased bars, configurable PWM brightness. See [the UI handoff](docs/UI_HANDOFF.md) and [design/extension guide](docs/UI.md). The notes below describe the earlier v1.1 baseline; its rotation, dimming, and unused-touch statements are superseded.

State as of 2026-10-21, tag `v1.1.0` on `main` (pushed to the private `zdhoward/AIUsageMonitor`). You reported the device working well.

## What exists

- **Firmware** (`firmware/AIUsageMonitor`) is flashed to the ESP32-2432S024C on COM6. Settings in `config.h`:
  - `DISPLAY_ROTATION 2`: portrait, traditional right edge up
  - `SHOW_REMAINING 1`: shows quota left
  - USB-serial transport (Wi-Fi is opt-in and untested)
- **Service** (`service/aimon`, Python 3.13 + pyserial):
  - Runs hidden via `pythonw` and serves `127.0.0.1:8797`.
  - Pushes a JSON line to the display every 5 s.
  - Starts at logon through the per-user scheduled task `AI Usage Monitor (aimon)`.
  - Control it with `scripts/service.ps1 start|stop|restart|status|install|uninstall`.
- **Tools:**
  - `scripts/build.ps1` (arduino-cli; TFT pins as flags)
  - `scripts/flash.ps1` (pauses and resumes the service's port)
  - `scripts/screenshot.py` (frame-buffer PNG; `--rot`, `--payload`)
- **Docs:**
  - `README.md`: usage, orientation and remaining/used settings
  - `docs/HARDWARE.md`
  - `docs/DATA_SOURCES.md`
  - `docs/TEST_REPORT.md`
  - `docs/PROJECT_LOG.md`

## Key decisions (details in docs/PROJECT_LOG.md)

- **Quota and reset credits** come from T3's provider caches (`~/.t3/caches/*.json`). There are no direct provider calls and no OAuth tokens are read.
- **Tokens and cost** come from local Claude and Codex transcripts, priced with T3's rate table. They are labelled as estimates.
- **Free models** come from OpenCode's DB. OpenRouter key status is polled every 10 min.
- **USB serial instead of Wi-Fi:** the PC is on Ethernet with a Public firewall profile.
- **Port 8797:** 8787 is used by another local service.

## Validation

- 22 service unit tests pass (`cd service; python -m unittest discover -s tests -t .`).
- On-device checks are listed in `docs/TEST_REPORT.md`:
  - boot and pin report
  - all four rotations
  - malformed input
  - no-data dimming
  - waiting screen
  - service restart
  - flashing while the service runs
  - remaining mode
  - reset label (fixture)

## Remaining / unverified

- Physical orientation and panel colours were not confirmed by a separate check; you reported the device working.
- A real USB unplug/replug, PC sleep, and the logon task firing at an actual logon have not been observed.
- `SHOW_REMAINING 0` and Wi-Fi mode compile but have never been flashed.
- Cost estimates have not been reconciled against T3's Usage page.

## Related changes made this session (outside this repo)

- `~/.claude/CLAUDE.md` (repo `zdhoward/claude-config`, private) has two commits ahead of origin, not pushed:
  - "delegate by default when running as Opus"
  - "create GitHub repos as private"
- `~/.agents/model-router` (repo `zdhoward/model-router`, private) has one commit ahead, not pushed: the lesson about the first real routing test, and HANDOFF item 5.
- `git status` in `~/.claude` warns about missing `skills-library/*` directories (agents-sdk, cloudflare, wrangler, ...). These are probably dangling links. Not investigated.

## Next actions

1. Push `claude-config` and `model-router` if you want those rule changes on GitHub.
2. Re-run a small multi-part task in a fresh session to test the new delegate-by-default rule. Record the results in the model-router scoreboard.
3. Optional: add an OpenRouter or NIM alert on the display, or a touch control to toggle remaining/used. The CST820 touch controller is present but unused.
