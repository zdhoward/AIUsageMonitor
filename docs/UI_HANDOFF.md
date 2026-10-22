# UI handoff — 2026-10-22

Implemented for v1.2.0: last-known quota caching, full-brightness stale data, portrait rotation 0, whole-screen tap cycling, account focus pages, and eased bars. See [UI.md](UI.md) for the design and extension points.

The user's acceptance preference is practical: run it, inspect the display, and avoid an elaborate test suite. Existing service tests remain the lightweight regression check. Screenshots under `docs/img/v1.2-*.png` come from the ESP32 framebuffer, not browser mockups.

For a future Claude visual pass, start with `ui.cpp` and preserve transport/model separation. The overview intentionally fits three accounts, while focus pages make reset times much larger. Test new typography against 240×320 and RGB332; built-in fonts 1, 2, and 4 are compiled. More than three accounts may require an overview paging/layout adjustment. Landscape details remain available but the new overview/focus design targets portrait.

Remaining physical acceptance: user confirms orientation on the mount, taps cycle once per release, and readability/motion at their actual viewing distance. No new provider calls, credentials, or dependencies were added. Cache does not persist across power loss. No remote push or PR is requested.
