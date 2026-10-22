# Display design

A quiet instrument panel below a monitor. Percent remaining and reset timing dominate; cached readings stay bright even when the link or a source ages.

## Exactly two views

Tap and release anywhere to cycle; long holds over 1.5 seconds are ignored. Serial `!NEXT` does the same. The registry in `ui.cpp` (`kStaticViews`) drives navigation and the dots, so a third static view would be one entry plus its renderer.

- **Console (default):** three fixed client cards — `CLAUDE A (CL1)`, `CLAUDE B (CL2)`, `CODEX` — mapped by account name, so service reordering does not move rows. Each card's largest number is the exact percent left in its most urgent measured window (highest used), labelled with that window (`5h`, `7d`). The second window is smaller and includes its reset where space allows. The main reset line reads `Reset 2h14m`, `Update due` after the deadline, or `Reset unavailable` when unknown. A green dot appears only for the account matching a measured running activity.
- **Details:** the original activity, peak, quota, token, and cost dashboard, unchanged.

Landscape uses 10px padding, header at y6..29, divider at 32, three 53px rows, and a footer near y213. Portrait stacks three ~80px cards with its own spacing. Both derive geometry from `width()`/`height()`, so all four rotations work.

## Freshness and unknown values

A client is `STALE` when its service source age exceeds `CLIENT_STALE_S` (1200s), the serial link times out, or the payload flags it. Cached numbers stay at full brightness; stale is a label, never a reason to hide the reading. The footer shows the oldest provider source age (`Updated 4m`) rather than pretending a fresh serial push means fresh provider data, plus `CONNECTED`, `STALE`, or `SOURCE ERROR`.

Unknown quotas show `--`, never `0%`. A real 0% remains distinct from unknown. Percentages are never averaged across windows.

## Palette and configuration

RGB565 values in `ui.cpp` come from: background `#101923`, panel `#202C3B`, text `#F3F6FA`, secondary `#AEBCCC`, healthy `#49D7A0`, warning `#F4BC52`, critical `#FF6B6B`. The 8-bit RGB332 framebuffer quantizes them; the panel blue is snapped up one step to retain a blue-gray surface rather than olive.

`config.h`: `DISPLAY_ROTATION` (0 default), `BACKLIGHT_LEVEL` (0..255, ESP32 LEDC on GPIO27), `UI_CRITICAL_LEFT` (20), `UI_WARNING_LEFT` (50), `CLIENT_STALE_S` (1200), `SHOW_REMAINING` (details mode), `UI_ANIMATION`. Bars ease quietly toward new values; exact numbers update immediately.

## Where Claude edits later

Start with `ui.cpp`: `drawConsole` and `drawClientCard` own the three-client console, `drawDetails` owns the legacy sections, and `kStaticViews` is the registry. Keep renderers separate from transport/model logic. `model.cpp` merges and ages cached data; `snapshot.py` builds the payload. `scripts/screenshot.py --feed --next 1 --out build/console.png` captures the next view without a tap.
