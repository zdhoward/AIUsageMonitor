# v1.15.1 — Weekly exhaustion and Antigravity reset fixes

Service-only patch; firmware stays at 1.15.0 (no reflash needed).

- When an account's 7d window has 0% left, its 5h window now shows 0% left too, on account tiles and on per-account proxy rings (e.g. Codex). Each account is judged on its own.
- Antigravity session and weekly countdowns use the earliest upcoming reset across Gemini models, so they match real refills.

## Verification

- 51 unit tests pass, including new tests for the tile and proxy-ring rules.
- Service restarted; the ESP32 (fw 1.15.0, COM6) acknowledges pushes.
