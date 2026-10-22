# Display design and extension guide

The display is a quiet peripheral below a monitor: usage and resets take priority over diagnostics. Black background, white type, muted labels, account accents, and usage-based green/amber/red bars reuse TFT_eSPI's built-in fonts and RGB332 framebuffer. No web framework or extra graphics library is involved.

## Views

Tap and release anywhere to advance: overview, one focus page per account, detailed dashboard, then overview. Long holds over 1.5 seconds are ignored. Serial `!NEXT` uses the same view action. Account pages are generated from the payload; adding an account needs no new screen code. The selected view survives incoming payloads, including account reorders, but resets on reboot.

- Overview: three accounts per page with large percentages and paired quota bars; small reset countdowns beneath each bar. A fourth account gets a second overview page instead of smaller rows.
- Focus: a single account with generous spacing and large reset countdowns, designed for reading at a distance.
- Details: the previous activity, quota, token, and cost dashboard.

## State and motion

Known quota percentages stay visible at full brightness through link loss, stale readings, missing accounts/windows, and passed reset deadlines. A passed reset says `awaiting update` rather than claiming the quota replenished. Missing readings before any measurement remain `--`. Header link age and account `CACHED` labels expose freshness without hiding readings.

The same fallback covers activity, subscription usage/sparkline/by-account, free/NIM, and OpenRouter: an absent or unavailable section keeps its last values, and countdowns/ages advance with elapsed time rather than looking refreshed. A present zero is a real reading and replaces the cached number. Account plan, accent, reset credits, and quota windows are kept by identity; an explicit zero reset-credit count clears them. The peak banner recomputes from retained windows and says `CACHED` when fresh peak data is absent. This is RAM caching, not persistence across power loss.

Bars interpolate toward new readings over roughly a second; numeric labels show the exact reading immediately. Set `UI_ANIMATION 0` in config.h to disable interpolation. Rendering uses a full framebuffer to avoid visible clears. Countdown timing is independent of animation.

## Where to change things

- `firmware/AIUsageMonitor/ui.cpp`: palette, text/bar primitives, `drawQuotaView`, easing, and the view registry. `buildViews()` prepends generated overview/focus pages; `kStaticViews` lists static pages. Add one `kStaticViews` entry plus a renderer and navigation, dispatch, and dots follow automatically. Keep renderers separate from transport/model logic.
- `model.cpp`: merges each section by identity, keeping absent fields and aging countdowns. Present readings, including zero, replace cached measurements.
- `AIUsageMonitor.ino`: CST820 I2C whole-screen button, debounce, serial commands.
- `config.h`: rotation 0 (traditional landscape left edge up), remaining/used mode, animation.
- `scripts/screenshot.py --feed --next 1 --out build/focus.png`: capture the next page without a physical tap. `--next` is relative to the current page.

## Hardware verification limits

Framebuffer screenshots prove layout and serial view cycling, not physical touch reliability, perceived motion, viewing distance, or panel orientation. Check those on the mounted device. Overview pages cap at three rows; focus pages keep larger reset text and, in portrait, drop to font 2 only when three windows share the page.
