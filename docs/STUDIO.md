# Scene Studio

Scene Studio is the local companion web application for AI Usage Monitor. It provides visual layout editing, screen captures from the physical display, live scene tuning, playlist assembly, Lospec palette browsing, and local background service configuration.

Run Scene Studio locally:
```bash
python -m studio
```
This opens the studio interface at `http://127.0.0.1:8798` (built with vanilla JavaScript and native browser primitives, with zero external frontend dependencies).

---

## Tabs Overview

1. **Layout**
   - Choose which pages appear on the display and drag to reorder them.
   - Configure screen orientation (Landscape, Landscape 180°, Portrait, Portrait 180°).
   - Toggle quota values between *Remaining* and *Used*.
   - Switch console layout between *Rows* (three accounts) and *Grid* (up to six accounts in paired rings).

2. **Screensaver**
   - Set inactivity timeouts (from 10 seconds to 1 hour).
   - Select which living scene plays when inactive.
   - Set per-page wake policies on new usage.

3. **Playlists**
   - Assemble multi-scene rotations with configurable durations.
   - Assign playlists as dedicated tap pages or as the screensaver scene.

4. **Library**
   - Browse built-in and imported scenes, pages, and captures.
   - Live hover preview powered by the client-side canvas player.
   - Open the **Scene Editor** to tune speed, frame timing, layer fits, effects, and theme shifts.
   - Import image layers (PNG, GIF, JPG, Aseprite) directly.
   - Search and import palettes from Lospec.

5. **Display**
   - Capture current frame buffer from hardware over USB serial (`!SHOT`).
   - Monitor real-time performance stats (frame render time in ms, fps, free heap memory).
   - Step to the next page (`!NEXT`) or enable continuous live screen polling.
   - Save captured moments directly to the Library with profile and git commit metadata.

6. **Settings** (Added in T-024)
   - Configure hardware serial link, background poll cadence, and automatic brightness.
   - Reads defaults from the service `Settings` model and writes to `service/aimon.config.json`.

---

## Service Settings & Hardening

The **Settings** tab allows editing local service configuration without manual JSON editing or credential exposure.

### Allowlisted Fields

Only non-secret, user-serviceable fields are exposed:

| Field | Type | Description / Bounds |
|---|---|---|
| `serial_port` | string | USB serial device (e.g. `"auto"`, `"COM3"`, `"/dev/ttyUSB0"`). Max 64 chars, no control chars. |
| `quota_refresh_s` | float | Lightweight poll interval (quota caches, activity). Range: 0.5s – 86400s. |
| `refresh_s` | float | Heavy poll interval (log aggregation, transcripts). Range: 1.0s – 86400s. |
| `limits_stale_s` | float | Threshold before usage data is flagged stale. Range: 10s – 2592000s. |
| `reset_warning_s` | int | Advance warning window to keep display awake before reset. Range: 0 – 604800s. |
| `auto_brightness_enabled` | bool | Toggle solar elevation-based brightness scaling. |
| `auto_brightness_lat` | float | Latitude coordinate (-90.0° to +90.0°). |
| `auto_brightness_lng` | float | Longitude coordinate (-180.0° to +180.0°). |
| `auto_brightness_tz` | string | IANA timezone (e.g. `"Europe/London"`). Validated via standard library `zoneinfo`. |
| `auto_brightness_day_duty` | int | PWM duty cycle during full daylight (0 – 255). |
| `auto_brightness_night_duty` | int | PWM duty cycle at night (0 – 255). |
| `auto_brightness_startup_duty` | int | Initial boot duty cycle (0 – 255). |
| `auto_brightness_transition_duration`| int | Sunset/sunrise fade window in minutes (0 – 1440). |
| `auto_brightness_smoothing_duration` | int | PWM step interpolation time in milliseconds (0 – 60000ms). |

### Security Model & Safety Guarantees

- **No Secrets Exposed**: Private keys (such as `openrouter_api_key`), internal paths (`t3_home`, `opencode_db`), bind addresses, and credentials are never exposed in GET responses or error messages.
- **Key Preservation**: Saving settings merges allowlisted keys into the existing configuration, preserving all private or unrecognized keys intact on disk.
- **Atomic File Replacement**: Saves write to a temporary file in the same directory (`service/.aimon.config.json.<uuid>.tmp`) before an atomic `os.replace`.
- **Fail-Safe on Malformed Input**: If an existing `aimon.config.json` contains malformed JSON or unreadable content, write operations fail safely with a clean error, refusing to overwrite the existing file.
- **Cross-Origin Write Protection**:
  - `Content-Type: application/json` is strictly required.
  - `Host` header must match loopback origins (`127.0.0.1`, `localhost`, `[::1]`).
  - `Origin` and `Referer` headers are validated to prevent cross-origin requests from foreign browser contexts.
  - Request body size is bounded (max 64 KB for settings).
- **Separation of Concerns**: Service settings are decoupled from profile save and flash actions. Saving settings does not trigger a firmware build, device flash, or automatic service restart. A clear notice indicates that a manual service restart is required to apply changes.

---

## Scene Editor Updates

- **Dead Controls Hidden**: In accordance with `sceneDraw` in firmware, sky top/bottom colour pickers are hidden when a scene contains a generator (where background sky is bypassed by the engine). Image scenes continue to show the sky gradient pickers.
- **Human-Readable Section Titles**: Generators display descriptive names (e.g. *Plasma settings*, *Digital Rain settings*, *Pixel Patterns settings*, *Campfire settings*).
- **Clear Labels & Units**: All generator numeric inputs include concise physical units (`px`, `px/s`, `%`, `s`).
- **Effects Section**: Renamed to *Weather & sky effects* for clarity.

---

## Validation & Tests

Run the test suite:
```bash
python -m unittest discover -s studio/tests
python -m compileall -q studio
node --check studio/web/studio.js studio/web/scene.js studio/web/settings.js studio/web/playlists.js
```
