# Display design

A quiet instrument panel below a monitor. Percent remaining and reset timing dominate; cached readings stay bright even when the link or a source ages.

## Default navigation entries

Tap and release anywhere to cycle; long holds over 1.5 seconds are ignored. Serial `!NEXT` does the same. The registry in `ui.cpp` (`kStaticViews`) drives navigation and the dots; stable page IDs (`UI_PAGE_*`) do not shift when optional pages are compiled out.

Default order: Console, Details, Companion, Images, Screensaver.
- **Console (default):** three fixed client rows — `CLAUDE A`, `CLAUDE B`, `CODEX` — mapped by account name, so service reordering does not move rows. The header groups `AI USAGE (3 CLIENTS)` at left and aligns **Session** (`5h`) and **Weekly** (`7d`) headings above their ring columns. Each ring centers exact percent remaining and eases clockwise from 12 o'clock. Its large, bright caption shows time until reset, `due` after a deadline, or `--` when unavailable. The data area beneath provider titles is intentionally empty for future use. Unknown quotas show `--`, distinct from empty 0% or full 100% rings.
- **Details:** the original activity, peak, quota, token, and cost dashboard, unchanged.
- **Companion:** loops between idle and happy expressions using existing drawing primitives. Renders without quota data.
- **Images:** centered explanatory placeholder text. Renders without quota data.
- **Screensaver:** normal navigation stop that previews the configured target (`UI_SCREENSAVER_PAGE`, default Companion) even while automatic activation is off. It is identified by replacing the target's header band with `SCREENSAVER`; the preview body/divider stays intact. Tap/`!NEXT` advances normally. The target must be an included, eligible page other than Screensaver; invalid targets fail at build time. Automatic activation remains off by default and is not implemented in this slice (T-008B).

Optional pages default on and are removable with one switch each in `config.h`: `UI_COMPANION_ENABLED`, `UI_IMAGE_ENABLED`, `UI_SCREENSAVER_ENABLED`. Console and Details remain available. Visual pages render without quota data; dashboard waiting behaviour remains for Console/Details.

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
