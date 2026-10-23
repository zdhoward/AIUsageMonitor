# Test report

## T-008A source/build checks (2026-10-23)

- Production build (`scripts/build.ps1`) passes: 414107 bytes flash, 28648 bytes static RAM, with default five entries after R3 corrective layout changes.
- `git diff --check` passes.
- Variant builds passed: disable Companion, disable Images, disable Screensaver entry, and all three optional pages disabled.
- Invalid target builds failed as intended: self-target, unknown target (99), disabled target, and disabled-target-with-activation-enabled.
- Subsequent authorized device pass: production main build flashed COM6 with esptool hash verification. Five default entries captured and serial `!NEXT` wrapped back to Console; service resumed fresh ACKs. Evidence: [Console](img/T-008A-console.png), [Details](img/T-008A-details.png), [Companion](img/T-008A-companion.png), [Images](img/T-008A-images.png), [Screensaver preview](img/T-008A-screensaver.png), [portrait Console](img/T-008A-portrait-console.png). Coordinator inspected these actual RGB332 frames; landscape footer/dots and preview identity are clear. Portrait source age truncates to `Updated~`. Restored rotation 1 and Console afterward.
- Physical taps, panel appearance, sustained animation/FPS, no-data boot, alternate saver targets and remaining runtime rotation variants remain pending. Companion/preview captures show Happy and Idle respectively, not a timing benchmark. Screensaver auto activation remains off and unimplemented (T-008B).
- Service tests were not run.
- Independent capture-review attempt could not view the PNGs; its favorable visual claims are unsupported and excluded. Rendered evidence above was inspected directly by the coordinator; no independent visual pass is claimed.

Current baseline, 2026-10-22: all 22 existing service tests pass; the service is healthy with firmware v1.4.2 / rotation 1. The firmware build, flash and framebuffer capture were completed before the public documentation work. Historical dimming/rotation observations below describe old firmware, not current behavior.

## v1.4.2 reset readability (2026-10-22)

- Firmware built successfully: 413,263 bytes flash, 28,648 bytes static RAM. Flashed with hash verification; device reports `rot=1 w=320 h=240 fb=1` and normal serial acknowledgements.
- [Current framebuffer](img/v1.4.2-rings.png) shows bright font 2 reset captions and rings moved up 6px. All six captions fit in their cards at the captured values. This verifies rendered geometry, not physical viewing-distance comfort.
- Existing 22 service tests pass. The deadline scheduler was inspected and the service restarted; automatic deadline wake-up has not been observed through a real reset or covered by a dedicated timer test. It rereads local T3 caches/transcripts, not provider endpoints.
- Documentation changes reuse this unchanged firmware baseline; no fresh hardware compatibility or optional Wi-Fi verification is claimed.

## v1.4.1 ring headings and captions (2026-10-22)

- Build and diff check pass; flashed device reports `rot=1 w=320 h=240` and normal acknowledgements. Framebuffer `img/v1.4.1-rings.png` verifies grouped title/client count, aligned Session/Weekly headers, reset countdowns under rings, and empty space beneath provider names.
- Parent completed and reviewed the small renderer adjustment after the delegated worker returned only a version edit; no independent review pass or additional test suite is claimed.

## v1.4.0 ring console (2026-10-22)

- ESP32 build and diff check pass. Framebuffer capture `img/v1.4.0-rings.png` shows Session and Weekly rings, correct real 0% readings, independent yellow weekly gauges, and muted reset rows. No test suite additions.
- Track contrast was increased after the first framebuffer capture: RGB332 quantized the original track and panel to the same shade, hiding empty rings. Parent also corrected arc origin to 12 o'clock and portrait table width after the worker stopped early.

## v1.3.3 quota bars (2026-10-22)

- Build and scoped ticket verification pass; no new tests needed for the renderer-only refinement. Local Ollama GPT-OSS review found no blockers after the cloud reviewer exhausted free quota.
- Flashed to COM6 and confirmed `rot=1 w=320 h=240`, normal serial acknowledgements. `img/v1.3.3-landscape.png` shows separate session and weekly bars with explicitly labeled resets and no clipping for the current three clients, including real 0% readings.

## Verified on the real device (COM6, ESP32-D0WD-V3)

| Check | Result | Evidence |
| --- | --- | --- |
| Chip identity, 4 MB flash | ESP32-D0WD-V3 rev 3.1 | `esptool chip-id`, `flash-id` |
| Firmware compiles for target | `esp32:esp32:esp32`, 28% flash, 8% RAM | `scripts/build.ps1` |
| All four rotations compile | 0, 1, 2, 3 OK | `build.ps1 -Rotation N` |
| Upload and boot | `@HELLO aimon-fw 1.0.0 rot=2 w=240 h=320 fb=1` | serial |
| Pin map compiled in | `@SETUP drv=9341 mosi=13 miso=12 sclk=14 cs=15 dc=2 rst=-1 bl=27 spi=40 MHz` | serial; matches HARDWARE.md |
| Full-frame buffer allocated | `fb=1` (8-bit, 76.8 KB), ~246 KB heap left | serial |
| Data arrives and is acknowledged | `@ACK <seq>` every 5 s; first ACK 3 s after service start | `logs/aimon.log`, `/healthz` |
| Opening the port doesn't reset the ESP32 | DTR/RTS de-asserted; no reboot seen | no `@HELLO` on connect |
| Layout in all four orientations | No clipping or overlap; landscape reflows into two columns | `docs/img/rot0-3.png` (frame-buffer dumps) |
| Malformed input | Truncated JSON and wrong version: `@ERR`; non-JSON and 5 KB oversize lines ignored; last good data kept | serial transcript |
| Service stopped | After 30 s, header shows `NO DATA 1m` in red; body dimmed but readable | `docs/img/test_nodata.png` |
| Device reboot with no service | "Waiting for data" screen with orientation marker | `docs/img/test_waiting.png` |
| Service restart | Device recovers within one push (≤5 s) | `/healthz` |
| Flash while service running | `flash.ps1` pauses the serial link, uploads, resumes | script output, log `serial.pause_requested` / `resume_requested` |
| Live quota change | CL2 session moved from 37% to 46% between captures as T3 refreshed | screenshots |

## v1.1.0 additions (verified on device)

| Check | Result | Evidence |
| --- | --- | --- |
| Remaining mode (`SHOW_REMAINING 1`) | Bars and % show quota left; banner `LOWEST 6% left CL1 7d`; colours still by usage | `docs/img/rot1.png`, `rot2.png` |
| Reset credits label | Fixture payload (`rc` 1 and 2) renders `Pro (1x reset)` / `Pro (2x resets)`; real accounts with 0 show `Pro` | frame-buffer capture from a fixture via `screenshot.py --payload` |
| Service passes `rc` only when > 0 | 2 new unit tests (22 total) | `service/tests` |

`SHOW_REMAINING 0` is a compile-time constant in the same code paths, so it builds in the same binary layout. It was not flashed.

## Verified in the service

- 22 unit tests (`service/tests`), all fixture-based with no network:
  - T3 cache parsing (malformed, irrelevant, and signed-out caches)
  - e-mail exclusion
  - Claude dedupe and incremental appends
  - partial lines and truncated files
  - Codex token and rate-limit parsing
  - activity selection (stale running rows ignored)
  - OpenCode v1/v2 tables and a missing database
  - OpenRouter parsing
  - reset credits (parsed, and sent only when above 0)
  - payload: unknown → `-1`, expired windows retain measured usage and report due, stale excluded from PEAK, source and OpenRouter errors surfaced, empty state
- Real data: 3 accounts, ~15.5k usage records, 43 free-model calls today. Refresh costs 2.5 s cold, then 40–55 ms per incremental pass every 10 s.
- The service runs hidden via `pythonw`. The logon task `AI Usage Monitor (aimon)` is registered.

## Not verified / assumptions

- **Physical orientation:**
  - Frame-buffer screenshots prove the image is rendered correctly for each rotation, not which way the panel physically faces.
  - `DISPLAY_ROTATION 2` = "traditional right edge up" is derived from the ILI9341 MADCTL table plus your sketches' `setRotation(1)` habit (HARDWARE.md).
  - **Needs one glance:** text should read upright with the board's former right edge on top. If it's upside down, set `0`.
- **Colour fidelity** on the physical panel. The frame buffer is RGB332; the screenshots show the quantized colours, but the panel's own colour order and inversion were not checked by eye. Earlier sketches used the same driver settings.
- **Unplug/replug of USB:** reconnect logic was exercised by pausing and resuming the port, not by physically pulling the cable.
- **PC sleep, logon task at a real logon, and T3 not running for hours:** not observed; staleness logic is unit-tested.
- **Wi-Fi mode:** compiles only when enabled; never run.
- **Cost estimates:**
  - They use T3's price table. Claude cache writes are priced at the input rate unless the table lists a cache-write price. Codex `input_tokens` are treated as including cached tokens (OpenAI convention).
  - The figures were not reconciled against T3's Usage page totals.

## v1.2.0 update (2026-10-22)

- Firmware compiles for the actual ESP32 target; 395,423 bytes flash and 28,432 bytes static RAM. Flashed with hash verification.
- Existing 22 service tests pass, including the revised requirement that expired windows retain their last measurement.
- Framebuffer captures: `img/v1.2-overview.png`, `img/v1.2-focus.png`, `img/v1.2-cached.png`. Serial `!NEXT` exercises the same view action as touch release.
- CST820 physical tapping, mounted orientation, perceived smoothness, and reading distance require user confirmation. No expanded test suite was added.

## v1.3.0 two-view console (2026-10-22)

- OpenCode DeepSeek implemented; OpenCode Beam reviewed with no blockers. Ticket verification passed: ESP32 build and scoped diff check. Existing service tests: 22 passed.
- Exactly two registry entries: console and original details. New renderer shows Claude A / Claude B / Codex, urgent remaining quota, reset countdown, a separate secondary window, stale labels, and oldest source age. PWM brightness and remaining-capacity thresholds are configurable.
- Device flashed with hash verification. Captures: `img/v1.3-console.png`, `img/v1.3-details.png`, `img/v1.3-landscape.png`. The blue component of the panel palette was adjusted after framebuffer inspection because RGB332 truncation made the literal requested color olive.
- Physical tap reliability, mounted orientation, and comfortable reading distance remain user checks; serial view cycling and rendered frames are observable here.
