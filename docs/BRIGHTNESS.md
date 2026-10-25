# Automatic backlight brightness

Powered by [SunriseSunset.io](https://sunrisesunset.io).

The PC service is the sole serial owner. A separate worker fetches solar schedules; device payload generation reads only memory. All views and screensavers share the backlight, and brightness updates do not wake idle views. No sun times appear on the ESP dashboard.

## Settings

Use `service/aimon.config.json` or the matching uppercase `AIMON_*` environment variable, then restart the service to reload. No reflash is needed for these settings. Environment booleans use JSON `true`/`false`; numbers must be numeric, without quotes. JSON booleans, fractions and strings are rejected for integer duty/duration settings.

| Setting | Default | Meaning |
| --- | --- | --- |
| `auto_brightness_enabled` | `true` | Disable to omit `bl` and `bl_ms`, with no solar HTTP or cache access |
| `auto_brightness_lat` | `51.4779` | Latitude, finite -90..90 |
| `auto_brightness_lng` | `-0.0015` | Longitude, finite -180..180 |
| `auto_brightness_tz` | `Europe/London` | IANA timezone |
| `auto_brightness_day_duty` | `255` | Integer PWM duty, 0..255 |
| `auto_brightness_night_duty` | `40` | Integer PWM duty, 0..day duty |
| `auto_brightness_startup_duty` | `80` | Integer PWM duty before any current-date schedule, 0..255 |
| `auto_brightness_transition_duration` | `60` | Integer minutes for each centred solar ramp, 0..1440 |
| `auto_brightness_smoothing_duration` | `1000` | Firmware interpolation duration, integer 0..60000 ms |
| `auto_brightness_refresh_s` | `86400` | Proactive refresh seconds, 0.1..604800 |
| `auto_brightness_retry_s` | `900` | Failure retry seconds, 0.1..604800 |
| `auto_brightness_http_timeout_s` | `5` | HTTP socket timeout seconds, 0.1..300 |
| `auto_brightness_worker_tick_s` | `60` | Worker cadence seconds, 0.1..300 |

Defaults are a placeholder location (Greenwich, London); set your own in `service/aimon.config.json`. PWM duty is not perceived brightness percent: 255 is full duty and 0 is off. Invalid enabled configuration fails startup rather than silently selecting another location. Windows needs the IANA `tzdata` package included in `service/requirements.txt`; Unix normally supplies a system timezone database.

## Scheduling and outages

The worker requests yesterday through the next seven dates using `lat`, `lng`, `date_start`, `date_end`, `timezone` and `time_format=unix`. It requires API `status=OK` and matching top-level `tzid`. Unix responses legitimately report per-item `timezone=UTC`; the configured `ZoneInfo` determines local dates and DST. String Unix epochs are accepted; dates, finite integer epochs and `sun_status` are validated. `normal` requires sunrise on the requested local date; sunset may extend past midnight into the following date. `midnight_sun` and `polar_night` require null events and produce constant day/night duty respectively. API errors including `INVALID_TZID` retain cached behavior.

Sunrise ramps from night to day; sunset ramps from day to night. The service uses smoothstep (`x*x*(3-2*x)`) inside centred windows. Events from yesterday/today/tomorrow are sorted by UTC epoch, including dates with sunset before sunrise. Each window is clipped at adjacent event midpoints so long windows cannot overlap across daylight or night gaps. Zero duration switches exactly at the event; the post-event value wins at the edge. Epoch arithmetic and local calendar dates handle DST without assuming a permanent UTC offset.

Cache files are keyed by coordinates/timezone under `%LOCALAPPDATA%/AIUsageMonitor/cache/sun-<hash>.json` on Windows, or `~/.cache/AIUsageMonitor/cache/` otherwise. Loading and HTTP responses are limited to 65536 bytes; cache retention is nine dates. Writes use a unique temporary file and atomic replacement. Invalid cache content is ignored with a status error; it cannot select another location. On restart, valid cached current-date events immediately determine duty. The controller does not persist a stale duty separately.

Refresh occurs proactively, on local date rollover, and for missing coverage, at worker cadence. Failures are throttled using monotonic time. Valid cached ramps continue advancing even when HTTP fails. If the current local date has no schedule, the latest computed duty is held (`held`); before any valid computation, startup duty is used (`startup`). Yesterday's schedule is never substituted for a missing current date. At restart with no current-date cache, startup duty applies until a successful fetch.

`--once` loads the cache and computes a current target or startup fallback without solar HTTP or threads. Other usage collectors retain their normal `--once` behavior.

## Wire and firmware

Enabled payloads include `bl` and `bl_ms`, including the service's oversized-payload fallback within the 4095-byte wire-line limit. Older firmware ignores these optional fields. Missing/invalid `bl` preserves the last target; explicit zero is valid. With valid `bl`, missing/invalid `bl_ms` preserves its last duration. No `bls` source label is sent.

GPIO27 remains 5 kHz, 8-bit LEDC. Boot uses `BACKLIGHT_LEVEL` (255) and `BACKLIGHT_SMOOTHING_MS` (1000). In `loop()`, a changed target interpolates linearly from the current duty over `bl_ms`, nonblocking and with wrap-safe unsigned `millis()` subtraction. Zero duration is instant; identical repeated targets do not restart interpolation. A disconnect retains the target, allowing an active ramp to finish. All screens share this application path.

## Troubleshooting and manual acceptance

Both `/healthz` and `/v1/status` expose a `brightness` object: mode, current duty/source, source date, current-date coverage, cache path/count, last fetch epoch, error, effective configuration, source name and attribution URL. Sources are `startup`, `held`, `day`, `night`, `transition`, `midnight_sun`, `polar_night`, or `disabled`. Check configuration and error first if duty does not change. Network/cache failures appear as `brightness.refresh_failed` or in the status error; a valid cache continues working through outages.

Pending owner hardware acceptance:

1. Confirm comfortable day/night PWM values and visible startup behavior on the physical panel.
2. Verify USB and Wi-Fi payloads accept 0/40/255, reject invalid values, interpolate for the configured duration, and apply 0 ms instantly.
3. Disconnect while interpolating and verify the target is retained; reconnect and confirm updates resume.
4. Verify all pages and screensavers share brightness and brightness-only changes do not wake idle views.
5. Observe a solar transition, outage/restart with cache, and rollover without coverage. Automated regression tests remain deferred to the owner testing phase.
