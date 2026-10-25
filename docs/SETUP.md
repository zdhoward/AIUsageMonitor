# Setup and operation

The tested host is Windows with PowerShell. The Python service uses the standard library plus pyserial; Linux/macOS support for the helper scripts is not claimed. The default transport is USB, with no Wi-Fi credentials or external board wiring required.

## MINT session state

Service startup allocates an ordered session in
`%LOCALAPPDATA%/AIUsageMonitor/mint-session.sqlite3` (fallback:
`~/.local/share/AIUsageMonitor/mint-session.sqlite3`). Keep this user-local file
across upgrades, checkouts and restarts; do not place it on a network share.
SQLite's immediate transaction and FULL synchronous commit serialize concurrent
allocations with a 10-second lock timeout. Storage must honor durable writes.
Allocation errors abort startup before any MINT publishing. Values cannot exceed
16 hex digits; exhaustion requires coordinated recovery, never wraparound.

Run only one active service per device. Concurrent startups receive unique IDs,
but a newer service retires the older service's identity. All instances serving
that device must use the same OS user's state, not separate copies/accounts.

If state is lost, restored from an older backup, or corrupt: stop every service,
restore the latest known state if available, otherwise move the damaged database
and any journal aside, reboot the device to clear its identity high-water, then
start one service to create fresh state. A rollback of state cannot safely bypass
the firmware's retired-session rejection. Do not delete state as routine repair
without that coordinated device reboot. Corrupt files are never auto-reset.

## 1. Install the host tools

Install Git, Python 3.13 and Arduino CLI (standalone, or bundled with Arduino IDE 2). A CH340 driver may be needed if Windows does not expose the board as a serial port. Use a USB data cable, not a charge-only cable.

Clone the repository and enter its directory. Run subsequent commands from the repository root unless stated otherwise:

```powershell
git clone https://github.com/zdhoward/AIUsageMonitor.git
Set-Location AIUsageMonitor
python -m pip install -r service/requirements.txt
```

The repository may be private until its owner publishes it. `pyserial==3.5` is the tested serial dependency. The service can run HTTP-only without pyserial, but USB output and screenshot capture require it. If using a virtual environment, activate it before running the helper scripts so they find the intended Python installation.

## 2. Install the firmware toolchain

The tested baseline is Arduino CLI **1.2.0**, ESP32 Arduino core **3.3.1**, TFT_eSPI **2.5.43**, and ArduinoJson **7.4.2**. These are the verified versions, not a promise that every newer version works. Wire, WiFi and HTTPClient come with the ESP32 core; no separate touch library is needed.

Locate the CLI in PowerShell:

```powershell
$arduinoCli = Join-Path $env:LOCALAPPDATA 'Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe'
if (-not (Test-Path $arduinoCli)) {
    $arduinoCli = (Get-Command arduino-cli -ErrorAction Stop).Source
}
& $arduinoCli version
```

Install the board package and libraries. The explicit board index flag avoids changing a shared Arduino configuration:

```powershell
$esp32Index = 'https://espressif.github.io/arduino-esp32/package_esp32_index.json'
& $arduinoCli core update-index --additional-urls $esp32Index
& $arduinoCli core install esp32:esp32@3.3.1 --additional-urls $esp32Index
& $arduinoCli lib update-index
& $arduinoCli lib install 'TFT_eSPI@2.5.43' 'ArduinoJson@7.4.2'
```

The build targets `esp32:esp32:esp32:FlashSize=4M,PartitionScheme=default`. TFT pin definitions are passed as compiler flags by the build script. Do not modify the global TFT_eSPI setup when using that script. Building manually in Arduino IDE requires reproducing those flags or an equivalent library setup; the script is the reproducible path.

## 3. Configure local data sources

```powershell
Copy-Item service/aimon.config.example.json service/aimon.config.json
```

Edit that local JSON file before starting the service. It is Git-ignored. The example disables optional OpenRouter polling; code defaults enable it when no override is supplied. To use OpenRouter, enable `openrouter_enabled` and make the key available in `OPENROUTER_API_KEY` or the existing OpenCode auth file. Never put keys in committed files or firmware.

| Setting | Meaning / default |
| --- | --- |
| `t3_home` | T3 data directory, `~/.t3`; `~` is expanded |
| `serial_port` | `auto`, or an explicit port such as `COM6` |
| `serial_baud` | 115200; must match firmware |
| `serial_enabled` | `true`; set false for HTTP-only operation |
| `bind_host`, `bind_port` | `127.0.0.1`, 8797 |
| `refresh_s` | Local collection cadence, 10 seconds, also shortened for upcoming reset deadlines |
| `push_interval_s` | Serial payload cadence, 5 seconds |
| `limits_stale_s` | Service staleness threshold, 3600 seconds (T3 re-polls Claude quota only every few minutes, and an idle account can go 10+ minutes between readings) |
| `openrouter_refresh_s` | Optional key-status polling cadence, 600 seconds |
| `opencode_refresh_s` | OpenCode history polling cadence, 30 seconds |
| `opencode_db` | Optional path override; default `~/.local/share/opencode/opencode.db` |
| `auto_brightness_enabled` | Automatic location-based backlight, default `true`; see [BRIGHTNESS](BRIGHTNESS.md) |
| `auto_brightness_lat`, `auto_brightness_lng`, `auto_brightness_tz` | Sunrise/sunset location; defaults are approximate the owner's city city-centre coordinates (`51.4779`, `-0.0015`, `Europe/London`) — not a street address |
| `auto_brightness_day_duty`, `auto_brightness_night_duty`, `auto_brightness_startup_duty` | PWM duty 0–255 for day, night and the startup/no-data fallback (255 / 40 / 80) |
| `auto_brightness_transition_duration` | Sunrise/sunset-centred ramp window in minutes, 60 |
| `auto_brightness_smoothing_duration` | Firmware target interpolation duration in milliseconds, 1000 (0..60000; 0 instant) |
| `auto_brightness_refresh_s`, `auto_brightness_retry_s` | Solar fetch refresh/retry seconds, 86400 / 900 |
| `auto_brightness_http_timeout_s`, `auto_brightness_worker_tick_s` | Solar HTTP timeout/worker cadence seconds, 5 / 60 |

Other settings and exact defaults live in [config.py](../service/aimon/config.py). `AIMON_<UPPERCASE_SETTING>` environment variables override the JSON file, for example `$env:AIMON_SERIAL_PORT = 'COM6'`. Environments of background/logon processes may differ from the terminal you use for setup.

T3 must have written provider status caches for quota readings. Claude and Codex transcript roots are discovered from T3 provider-instance settings, with standard home-directory fallbacks. A missing price table at `~/.t3/userdata/usage-model-rates.json` leaves affected token costs unpriced. No login refresh or direct subscription usage request is performed by this service.

### Console account names

The console has three fixed slots. Set the desired provider display names in T3 to **CL1**, **CL2** and **Codex**. Case-insensitive names beginning with **Claude A**, **Claude B** and **Codex** are also accepted. Account names in payloads are truncated to eight characters; keep names short. Names are read from local settings/cache data; the monitor does not change T3 settings.

Session and Weekly rings are selected by window labels **5h** and **7d**. Different account counts, names or window durations require changing `slotIndex`, `kClientName` or window selection in [ui.cpp](../firmware/AIUsageMonitor/ui.cpp). Unknown mappings stay `--`; they are not guessed from account order.

## 4. Build, flash and run

Connect the documented board, then run:

```powershell
.\scripts\build.ps1
.\scripts\flash.ps1
.\scripts\service.ps1 start
.\scripts\service.ps1 status
```

`build.ps1` uses the bundled Arduino IDE CLI or a standalone CLI on PATH. Outputs go to `build/`. `flash.ps1` detects the documented CH340 bridge, uses esptool installed with the ESP32 core, and coordinates port release with an already-running service. You can specify a port with `-Port COM6`; the number is an example, not a board requirement.

For foreground logs or a one-shot payload:

```powershell
Push-Location service
python -m aimon --once
# Or run continuously in the foreground:
python -m aimon --port COM6 -v
Pop-Location
```

Stop the background service before starting a second process on the same port. `--once` may perform optional OpenRouter status access if enabled; it is not the fixture test command.

Service management:

```powershell
.\scripts\service.ps1 restart
.\scripts\service.ps1 stop
.\scripts\service.ps1 install    # optional per-user logon task
.\scripts\service.ps1 uninstall
```

Background execution uses `pythonw` when available. Logs go to `logs/aimon.log`. The optional scheduled-task name is `AI Usage Monitor (aimon)`. Installation was exercised on the development host; execution at a real subsequent logon has not been observed.

## 5. Customize the screen

MINT behavior runs with the existing service. To react locally (no serial port
is opened by the request):

```powershell
Invoke-RestMethod -Method Post 'http://127.0.0.1:8797/v1/mint/react?action=pet'
```

Use `play` or `nap` for the other finite reactions. No body is accepted. Same
action repeats coalesce; a different action while busy returns 429. Reactions
are loopback-only even when HTTP is bound to a LAN address. Optional Windows
CPU/RAM stress is off by default; set `"mint_metrics_enabled": true` in
`service/aimon.config.json` (or `AIMON_MINT_METRICS_ENABLED=true`) and restart.
See [MINT](MINT.md) for timing and [protocol](PROTOCOL.md) for lease semantics.

Edit [config.h](../firmware/AIUsageMonitor/config.h), rebuild and flash:

- `DISPLAY_ROTATION`: 1 by default; 0/2 portrait, 1/3 landscape.
- `BACKLIGHT_LEVEL`: 0–255 PWM duty, default 255.
- `BACKLIGHT_SMOOTHING_MS`: boot linear interpolation duration, default 1000ms; service `bl_ms` overrides it.
- `UI_CRITICAL_LEFT`, `UI_WARNING_LEFT`: remaining-quota color thresholds, 20 and 50.
- `CLIENT_STALE_S`: firmware source-age threshold; keep consistent with service settings if changed.
- `UI_ANIMATION`: restrained ring animation on/off.
- `SHOW_REMAINING`: detailed dashboard only; console rings always show remaining quota.
- `UI_COMPANION_ENABLED`, `UI_IMAGE_ENABLED`: default-on optional navigation entries (1/0).
- `UI_SCREENSAVER_ENABLED`, `UI_SCREENSAVER_AUTO_ENABLED`: both default on; either can disable automatic saving.
- `UI_SCREENSAVER_PAGE`: automatic target, default `UI_PAGE_COMPANION`; must be compiled in when saving is active.
- `UI_HOME_PAGE`, `UI_HOLD_MS`: long-press home target (default `UI_PAGE_CONSOLE`) and hold time (default 700 ms).
- `UI_SCREENSAVER_TIMEOUT_MS`: default 30000. Override each view with `UI_CONSOLE_SAVER_TIMEOUT_MS` / `UI_DETAILS_SAVER_TIMEOUT_MS`.
- `UI_CONSOLE_SAVER_ENABLED`, `UI_DETAILS_SAVER_ENABLED`: per-view saving, default 1.
- `UI_CONSOLE_WAKE_ON_USAGE`, `UI_DETAILS_WAKE_ON_USAGE`: per-view automatic wake, default 1.

Restart-to-reload: change any setting in `aimon.config.json` and restart the service; the brightness controller reinitializes with the new location/timezone.

See [BRIGHTNESS](BRIGHTNESS.md) for automatic backlight configuration, sunrise/sunset behavior, and troubleshooting.

Windows needs the IANA `tzdata` package from `service/requirements.txt` for `zoneinfo`. Invalid enabled brightness configuration fails startup clearly. `--once` uses valid cached schedules or duty 80 without solar HTTP or a brightness worker. Disabling automatic brightness omits `bl`/`bl_ms` and needs no solar network/cache access.

Tap and release anywhere to cycle the four available views. Holds of 1.5 seconds or longer are ignored. Console/Details sleep after 30 seconds without usage changes and wake on a change; Face/Images are exempt. A tap while asleep wakes the same view. Screensaver is absent from navigation. See [UI.md](UI.md) for comparison rules and policy details.

## Screenshots and checks

```powershell
python scripts/screenshot.py --feed --out build/dashboard.png
python scripts/screenshot.py --feed --next 1 --out build/other-view.png
```

`--next 1` advances from the current view, so it is not an absolute “details” selector. `--rot N` changes rotation until reboot. Screenshots capture the device's RGB332 framebuffer, enlarged 2× by default; `--scale 1` preserves native dimensions. The helper pauses/resumes the service around serial access.

From `service/`, run `python -m unittest discover -s tests -t .` for the 22 fixture-based tests. See the [test report](TEST_REPORT.md) for hardware evidence and remaining assumptions.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No CH340 port | USB data cable, Windows device detection and bridge driver; match the actual board variant |
| Access denied on serial port | Close Arduino Serial Monitor/other clients; use coordinated flash/screenshot helpers |
| Unknown console rows | T3 cache exists, display names match supported slots, windows use 5h/7d labels |
| `due` remains after reset | Wait for T3/provider cache or transcript to update; rereading a cache does not force a provider query |
| Fresh USB but `STALE` data | Check provider `checked_at`; delivery time and measurement time differ |
| Missing token costs | T3 price table exists and includes those models; figures are estimates, not subscription billing |
| Firmware build fails | Verify pinned libraries/core and CLI path; target this project's ILI9341 variant |
| `TOUCH_CS` warning | Expected for CST820 I²C touch; TFT_eSPI SPI touch is unused |
| HTTP bind failure | Port 8797 may already be occupied; don't start duplicate service instances |

## Optional Wi-Fi

USB is the verified default. Wi-Fi mode has not been tested on hardware. To experiment, copy `firmware/AIUsageMonitor/secrets.example.h` to ignored `secrets.h`, enter local Wi-Fi values and a reachable `AIMON_URL`, then set `AIMON_USE_WIFI=1`, rebuild and flash. Configure the service to bind to a reachable PC address and deliberately permit the port on a trusted network.

The HTTP API has no authentication, including its serial pause/resume controls. Do not expose it to the public Internet. Wi-Fi credentials remain on the device in this optional mode; subscription credentials do not. See [the protocol/API reference](PROTOCOL.md).
