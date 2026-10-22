# UI handoff — v1.4.2

The console uses Session and Weekly circular progress rings side by side, with percent remaining centered. Weekly is yellow; session follows capacity thresholds. Shared column headings sit above the rings; reset countdowns use bright font 2 beneath each ring, with rings raised 6px for clearance. The area below provider titles stays empty. The title groups `AI USAGE (3 CLIENTS)` at left. Heading and ring alignment share `ringCenterX`. Current evidence: [framebuffer capture](img/v1.4.2-rings.png).

Landscape rotation 1 is the persistent default, matching the user's final mounting instruction. The earlier portrait default was superseded. Both layouts remain available through `DISPLAY_ROTATION`.

Rendering clears explicit canvas dimensions so the rotated framebuffer has no leftover startup text along the right edge.

Two views only: a three-client console (default) and the original detailed dashboard. Generated overview and focus pages are removed. The console maps CL1, CL2, and Codex to stable rows. Session (`5h`) is the left ring and weekly (`7d`) the right ring. Cached numbers stay bright and carry a per-client `STALE` label; the footer shows oldest source age and link status.

Also in this change: retained quota windows now age their reset countdowns, cached OpenRouter numbers stay visible with an error marker instead of disappearing, the service emits `rc` for a known zero reset-credit count, and the backlight uses configurable LEDC PWM (`BACKLIGHT_LEVEL`). See [UI.md](UI.md) for layout, palette, and extension points.

Physical acceptance remains with the user: orientation on the mount, one view change per tap release, and readability at viewing distance. No new provider calls, credentials, or dependencies were added.
