# Display design

A quiet instrument panel below a monitor. Percent remaining and reset timing dominate; cached readings stay bright even when the link or a source ages.

## Exactly two views

Tap and release anywhere to cycle; long holds over 1.5 seconds are ignored. Serial `!NEXT` does the same. The registry in `ui.cpp` (`kStaticViews`) drives navigation and the dots, so a third static view would be one entry plus its renderer.

- **Console (default):** three fixed client rows — `CLAUDE A`, `CLAUDE B`, `CODEX` — mapped by account name, so service reordering does not move rows. Each row has two circular gauges: **Session** (`5h`) left, **Weekly** (`7d`) right. The centered number is exact percent remaining; the ring eases clockwise from 12 o'clock. Muted gray reset-table entries under the provider name use `S reset` and `W reset`, with `due` after a deadline and `--` when unavailable. Unknown quotas have dashed tracks and `--`, distinct from empty 0% or full 100% rings. Redundant account IDs and large extra percentages are removed.
- **Details:** the original activity, peak, quota, token, and cost dashboard, unchanged.

Landscape uses 10px padding, a slim header at y4..20, divider at 22, three 64px rows starting at y24, and a footer at y222. Portrait stacks three taller cards with 4px gaps and wider spacing between lines. Both derive geometry from `width()`/`height()`, so all four rotations work.

## Freshness and unknown values

A client is `STALE` when its service source age exceeds `CLIENT_STALE_S` (1200s), the serial link times out, or the payload flags it. Cached numbers stay at full brightness; stale is a label, never a reason to hide the reading. The footer shows the oldest provider source age (`Updated 4m`) rather than pretending a fresh serial push means fresh provider data, plus `CONNECTED`, `STALE`, or `SOURCE ERROR`.

Unknown quotas show `--`, never `0%`. A real 0% remains distinct from unknown. Percentages are never averaged across windows.

Weekly rings and their centered numbers are yellow for quick identification. Session rings and numbers follow remaining-capacity warning colors. Reset details are muted gray so the rings dominate.

## Palette and configuration

RGB565 values in `ui.cpp` come from: background `#101923`, panel `#202C3B`, text `#F3F6FA`, secondary `#AEBCCC`, healthy `#49D7A0`, warning `#F4BC52`, critical `#FF6B6B`. The 8-bit RGB332 framebuffer quantizes them; the panel blue is snapped up one step to retain a blue-gray surface rather than olive.

`config.h`: `DISPLAY_ROTATION` (1 default, landscape), `BACKLIGHT_LEVEL` (0..255, ESP32 LEDC on GPIO27), `UI_CRITICAL_LEFT` (20), `UI_WARNING_LEFT` (50), `CLIENT_STALE_S` (1200), `SHOW_REMAINING` (details mode), `UI_ANIMATION`. Bars ease quietly toward new values; exact numbers update immediately.

## Where Claude edits later

Start with `ui.cpp`: `drawConsole` and `drawClientCard` own the three-client console, `drawDetails` owns the legacy sections, and `kStaticViews` is the registry. Keep renderers separate from transport/model logic. `model.cpp` merges and ages cached data; `snapshot.py` builds the payload. `scripts/screenshot.py --feed --next 1 --out build/console.png` captures the next view without a tap.
