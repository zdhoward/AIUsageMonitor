# UI handoff — 2026-10-22

Implemented for v1.2.0: last-known quota caching, full-brightness stale data, portrait rotation 0, whole-screen tap cycling, account focus pages, eased bars, and a small view registry. Cache fallback now covers activity, usage, free/NIM, and OpenRouter; absent fields keep their last values, explicit zeros replace them, and countdowns stay aged. See [UI.md](UI.md) for the design and extension points.

The user's acceptance preference is practical: run it, inspect the display, and avoid an elaborate test suite. Existing service tests remain the lightweight regression check. Screenshots under `docs/img/v1.2-*.png` come from the ESP32 framebuffer, not browser mockups.

For a future Claude visual pass, start with `ui.cpp` and preserve transport/model separation. `buildViews()` generates overview pages (three rows each, so a fourth account gets page two) and account focus pages; add a static page by registering one entry in `kStaticViews` plus its renderer. Selection follows the account name, so payload reorders keep the focus page. In portrait, focus pages use font 4 reset text for one or two windows and font 2 for three so nothing overlaps. Test new typography against 240×320 and RGB332; built-in fonts 1, 2, and 4 are compiled. Landscape details remain available but the overview/focus design targets portrait.

Remaining physical acceptance: user confirms orientation on the mount, taps cycle once per release, and readability/motion at their actual viewing distance. No new provider calls, credentials, or dependencies were added. Cache does not persist across power loss. No remote push or PR is requested.
