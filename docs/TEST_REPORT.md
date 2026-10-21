# Test report: v1.0.0 (2026-10-21)

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

- 20 unit tests (`service/tests`), all fixture-based with no network:
  - T3 cache parsing (malformed, irrelevant, and signed-out caches)
  - e-mail exclusion
  - Claude dedupe and incremental appends
  - partial lines and truncated files
  - Codex token and rate-limit parsing
  - activity selection (stale running rows ignored)
  - OpenCode v1/v2 tables and a missing database
  - OpenRouter parsing
  - payload: unknown → `-1`, expired windows → unknown, stale excluded from PEAK, source and OpenRouter errors surfaced, empty state
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
