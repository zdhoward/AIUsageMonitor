# Display design

A quiet instrument panel below a monitor. Percent remaining and reset timing dominate; cached readings stay bright even when the link or a source ages.

In the Console grid, a known `7d` reset countdown turns white when less than 24 hours remain. At 24 hours or more it keeps the muted colour; unknown and `due` captions also keep the muted colour. Weekly rings, labels and percentages retain their usual colours.

## Default navigation entries

Tap and release anywhere to cycle. Hold anywhere for 0.7 seconds (`UI_HOLD_MS`) to jump home to `UI_HOME_PAGE`, the AI Usage console by default; this also leaves the screensaver or a `!SHOW` page. Serial `!NEXT` does the same. The registry in `ui.cpp` (`kStaticViews`) drives navigation and the dots; stable page IDs (`UI_PAGE_*`) do not shift when optional pages are compiled out.

Default order: Console, Details, Companion, Images.
- **Console (default):** three fixed client rows — `CLAUDE A`, `CLAUDE B`, `CODEX` — mapped by account identity, so service reordering does not move rows. `A`/`B` and `Claude A`/`Claude B` are accepted alongside `CL1`/`CL2`; other providers (Antigrav, Argon, Gemini, GPT) never fall into a Claude row. The header groups `AI USAGE (3 CLIENTS)` at left and aligns **Session** (`5h`) and **Weekly** (`7d`) headings above their ring columns. Each ring centers exact percent remaining and eases clockwise from 12 o'clock. Its large, bright caption shows time until reset, `due` after a deadline, or `--` when unavailable. The data area beneath provider titles is intentionally empty for future use. Unknown quotas show `--`, distinct from empty 0% or full 100% rings.
- **Details:** the original activity, peak, quota, token, and cost dashboard, unchanged.
- **Companion:** loops between idle and happy expressions using existing drawing primitives. Renders without quota data.
- **Images:** centered explanatory placeholder text. Renders without quota data.
- **Console grid (optional, profile `console_layout: "grid"`, set in Default):** six cells, 3x2 landscape and 2x3 portrait. Session/5h ring outside for greater detail, Weekly inside (remaining quota, clockwise). Each cell shows the account name, a running dot, `STALE` when old, and two labelled lines (window label, percent left, reset). Unknown is `--`; empty slots stay blank. In landscape, once the named five-account set is present the cells are pinned: **A top left, Codex top centre, Antigrav top right; B bottom left, bottom centre reserved and entirely empty, Argon bottom right.** The reserved cell is never filled with an unrelated provider. Argon has no independent source today, so it shows `--` rings and lines; the payload/status carry the reason `no independent quota`. Portrait and setups without the named set keep the generic first-six service order; additional accounts beyond six are not displayed. Landscape was captured on the display with four live accounts (`build/console-grid.png`); the pinned five-cell layout awaits its own flashed capture.
- **Screensaver:** automatic presentation of `UI_SCREENSAVER_PAGE` (default Companion), without a preview title or navigation dots. Console and Details enter it after 60 seconds without meaningful usage changes. A change restores the selected dashboard and starts another 60-second interval. Tap/`!NEXT` while asleep restores the same dashboard; the following tap navigates. Companion and Images never automatically sleep.

Each dashboard has separate `UI_CONSOLE_SAVER_ENABLED` / `UI_DETAILS_SAVER_ENABLED`, `UI_CONSOLE_SAVER_TIMEOUT_MS` / `UI_DETAILS_SAVER_TIMEOUT_MS`, and `UI_CONSOLE_WAKE_ON_USAGE` / `UI_DETAILS_WAKE_ON_USAGE` settings. Both wake flags default to 1; setting one to 0 keeps that view asleep until touch/navigation input. Entering a view starts a fresh interval. Either `UI_SCREENSAVER_ENABLED=0` or `UI_SCREENSAVER_AUTO_ENABLED=0` disables automatic saving globally. Targets must be compiled in; invalid active targets fail compilation.

Usage comparison includes quota percentages, account/window identity, availability/errors, costs, tokens, request counts and activity state/model. It ignores packet sequence, clock, reset countdown, source age/staleness and MINT updates. Repeated identical measurements do not wake the display. Policies are for logical views on this panel, not independent physical displays.

A separate visibility rule overrides saving and the usage-change wake switches:
any reported window that is `due` with known usage below 100% used keeps the
dashboard awake and wakes an active saver. Unknown usage/reset times and fully
used windows do not block saving. See [screensaver acceptance](SCREENSAVER.md).

Optional pages default on and are removable with `UI_COMPANION_ENABLED` and `UI_IMAGE_ENABLED` in `config.h`. Console and Details remain available. Visual pages render without quota data; dashboard waiting behaviour remains for Console/Details.

Landscape uses 10px padding, a slim header at y4..20, divider at 22, three 64px rows starting at y24, and a footer at y222. Portrait stacks three taller cards with 4px gaps and wider spacing between lines. Both derive geometry from `width()`/`height()`, so all four rotations work.

## Freshness and unknown values

A client is `STALE` when its service source age exceeds `CLIENT_STALE_S` (3600s), the serial link times out, or the payload flags it. Cached numbers stay at full brightness; stale is a label, never a reason to hide the reading. The footer shows the newest provider reading age (`Updated 2m`) rather than the serial push age, led by a link dot: green receiving, amber no payload for 30 s, red source error. An old reading on one account shows as that card's `STALE` label.

Unknown quotas show `--`, never `0%`. A real 0% remains distinct from unknown. Percentages are never averaged across windows.

Weekly rings and their centered numbers are yellow for quick identification. Session rings and numbers follow remaining-capacity warning colors. Reset captions use bright font 2 for distance readability; rings sit 6px higher to leave room beneath them.

The service wakes at upcoming reset deadlines to reread T3's usage cache and local transcripts, then continues normal polling while a deadline remains due. This does not force T3 to query providers; cached measurements stay visible until T3 or the transcripts supply new usage.

## Palette and configuration

RGB565 values in `ui.cpp` come from: background `#101923`, panel `#202C3B`, text `#F3F6FA`, secondary `#AEBCCC`, healthy `#49D7A0`, warning `#F4BC52`, critical `#FF6B6B`. The 8-bit RGB332 framebuffer quantizes them; the panel blue is snapped up one step to retain a blue-gray surface rather than olive.

`config.h`: `DISPLAY_ROTATION` (1 default, landscape), `BACKLIGHT_LEVEL` (0..255, ESP32 LEDC on GPIO27), `UI_CRITICAL_LEFT` (20), `UI_WARNING_LEFT` (50), `CLIENT_STALE_S` (3600), `SHOW_REMAINING` (details mode), `UI_ANIMATION`. Bars ease quietly toward new values; exact numbers update immediately.

## Where Claude edits later

Start with `ui.cpp`: `drawConsole` and `drawClientCard` own the three-client console, `drawDetails` owns the legacy sections, and `kStaticViews` is the registry. Keep renderers separate from transport/model logic. `model.cpp` merges and ages cached data; `snapshot.py` builds the payload. `scripts/screenshot.py --feed --next 1 --out build/console.png` captures the next view without a tap.
