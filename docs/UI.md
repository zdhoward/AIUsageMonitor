# Display design

A quiet instrument panel below a monitor. Percent remaining and reset timing dominate; cached readings stay bright even when the link or a source ages.

## Navigation pages

Tap and release anywhere to cycle; holds of 1.5 seconds or longer are ignored. Serial `!NEXT` does the same, including consuming the first action to wake a screensaver. The registry in `ui.cpp` (`kStaticViews`) drives navigation and the dots. With defaults, the order is Console, Details, Companion, Images, then Console.

- **Companion:** a small vector face alternates idle and happy every three seconds (six-second loop), using the existing refresh cadence and framebuffer. This is a future companion placeholder, independent of quota animation.
- **Images / animation:** centered explanatory text only. Conversion, storage and playback are not implemented.

The optional pages work even before telemetry arrives. Console and Details retain their waiting screen until data arrives. `UI_COMPANION_ENABLED` and `UI_IMAGE_ENABLED` default to `1`; setting either to `0` removes its renderer, navigation stop and dot.

## Screensaver

`UI_SCREENSAVER_ENABLED` defaults to `0`. Set it to `1` to display `UI_SCREENSAVER_PAGE` after `UI_SCREENSAVER_TIMEOUT_MS` without touch/navigation activity (default 60000 milliseconds). Select a stable ID: `UI_PAGE_CONSOLE`, `UI_PAGE_DETAILS`, `UI_PAGE_COMPANION` (default), or `UI_PAGE_IMAGE`. Selecting a disabled/unknown page or a timeout outside 1..2147483647 causes a compile error when the saver is enabled.

The saver temporarily renders the selected available page; it does not change the navigation selection or backlight brightness. Its dot indicates the page being displayed. A valid tap wakes to the prior selected page without advancing; the next tap advances normally. Holds keep the inactivity timer refreshed and remain ignored on release. Serial `!NEXT` uses the same wake/navigation action. Telemetry and screenshot commands do not reset inactivity; telemetry continues updating while the saver is visible. Configuration is build-time only, with no settings page or additional image buffers.

- **Console (default):** three fixed client rows — `CLAUDE A`, `CLAUDE B`, `CODEX` — mapped by account name, so service reordering does not move rows. The header groups `AI USAGE (3 CLIENTS)` at left and aligns **Session** (`5h`) and **Weekly** (`7d`) headings above their ring columns. Each ring centers exact percent remaining and eases clockwise from 12 o'clock. Its large, bright caption shows time until reset, `due` after a deadline, or `--` when unavailable. The data area beneath provider titles is intentionally empty for future use. Unknown quotas show `--`, distinct from empty 0% or full 100% rings.
- **Details:** the original activity, peak, quota, token, and cost dashboard, unchanged.

Landscape uses 10px padding, a slim header at y4..20, divider at 22, three 64px rows starting at y24, and a footer at y222. Portrait stacks three taller cards with 4px gaps and wider spacing between lines. Both derive geometry from `width()`/`height()`, so all four rotations work.

## Freshness and unknown values

A client is `STALE` when its service source age exceeds `CLIENT_STALE_S` (1200s), the serial link times out, or the payload flags it. Cached numbers stay at full brightness; stale is a label, never a reason to hide the reading. The footer shows the oldest provider source age (`Updated 4m`) rather than pretending a fresh serial push means fresh provider data, plus `CONNECTED`, `STALE`, or `SOURCE ERROR`.

Unknown quotas show `--`, never `0%`. A real 0% remains distinct from unknown. Percentages are never averaged across windows.

Weekly rings and their centered numbers are yellow for quick identification. Session rings and numbers follow remaining-capacity warning colors. Reset captions use bright font 2 for distance readability; rings sit 6px higher to leave room beneath them.

The service wakes at upcoming reset deadlines to reread T3's usage cache and local transcripts, then continues normal polling while a deadline remains due. This does not force T3 to query providers; cached measurements stay visible until T3 or the transcripts supply new usage.

## Palette and configuration

RGB565 values in `ui.cpp` come from: background `#101923`, panel `#202C3B`, text `#F3F6FA`, secondary `#AEBCCC`, healthy `#49D7A0`, warning `#F4BC52`, critical `#FF6B6B`. The 8-bit RGB332 framebuffer quantizes them; the panel blue is snapped up one step to retain a blue-gray surface rather than olive.

`config.h`: `DISPLAY_ROTATION` (1 default, landscape), `BACKLIGHT_LEVEL` (0..255, ESP32 LEDC on GPIO27), `UI_CRITICAL_LEFT` (20), `UI_WARNING_LEFT` (50), `CLIENT_STALE_S` (1200), `SHOW_REMAINING` (details mode), `UI_ANIMATION`. Bars ease quietly toward new values; exact numbers update immediately.

## Where Claude edits later

Start with `ui.cpp`: `drawConsole` and `drawClientCard` own the three-client console, `drawDetails` owns the legacy sections, and `kStaticViews` is the registry. Keep renderers separate from transport/model logic. `model.cpp` merges and ages cached data; `snapshot.py` builds the payload. `scripts/screenshot.py --feed --next 1 --out build/console.png` captures the next view without a tap.
