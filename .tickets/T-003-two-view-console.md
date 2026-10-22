---
id: T-003
title: Exactly two views with a glanceable three-client console
task_type: feature
lane: implement
critical: false
files:
  - firmware/AIUsageMonitor/ui.cpp
  - firmware/AIUsageMonitor/model.cpp
  - firmware/AIUsageMonitor/config.h
  - firmware/AIUsageMonitor/AIUsageMonitor.ino
  - service/aimon/snapshot.py
  - service/tests/test_service.py
  - docs/UI.md
  - docs/UI_HANDOFF.md
acceptance:
  - powershell -NoProfile -File scripts/build.ps1
  - git diff --check
---

## Goal
Finish promptly: exactly TWO tap-cycled views: new three-client console (default) and original detailed dashboard. User explicitly rejects extra client pages/research/test expansion. Reuse render primitives and keep the small registry, remove generated focus/overview pages. No extra views.

## User's final UI specification
Miniature instrument panel below a monitor. Percent remaining and reset timing dominate. Actual device verified: ESP32-2432S024C, ILI9341 TFT_eSPI, 240x320 portrait or 320x240 landscape. Keep rotation 0 default (current landscape left becomes portrait top), support all four rotations via config and responsive geometry.
New view: dark low-glare BG #101923, panel #202C3B, text #F3F6FA, secondary #AEBCCC, healthy #49D7A0, warning #F4BC52, critical #FF6B6B, quantized to RGB565/RGB332. Three stable rows/cards CLAUDE A (CL1), CLAUDE B (CL2), CODEX (Codex). No invented readings or activity. Largest item exact percentage left from the more urgent measured window (highest used); label that window (5h,7d,etc), NEVER average quotas. Unknown: --. Second quota smaller but legible, with reset info where space permits. Thresholds configurable (remaining <=20 critical, <=50 warning defaults). Header AI USAGE and client count, footer updated age + CONNECTED / STALE / SOURCE ERROR. Cached numbers stay bright; stale marked per client if source age >1200s OR link timeout OR a.stale. Valid 0 remains distinct from unknown. A running account matches m.actP (CL1/CL2/Codex); do not claim other accounts IDLE without real data: omit or use neutral state.
Landscape target: 10px padding, header y6..29, divider32, 3 rows y37..202 (~55px each), footer y213..233. Portrait uses its own spacing and 3 stacked readable cards (~85px each). Use built-in font4 (~26px) for large percentage, font2 (~16px) for names/reset/critical text. Increase percentage with text sizing if it fits; avoid tiny critical font1 text. No giant headings or decorations at expense of resets. Main reset must always fit: e.g. 'Reset 2h14m', 'Update due', 'Reset unavailable'. Quiet eased bars, exact numbers immediate, no constant pulse in the new view. Footer last update age must be visible; expose source age for new view (oldest client checked age) rather than pretending a new serial push means fresh provider data.
Brightness configurable (0..255), using ESP32 3.3.1 ledcAttach/ledcWrite on backlight GPIO27; rotation and refresh already config constants. No UI settings menu or persistence needed. Set FW_VERSION 1.3.0.

## Required bounded fixes
1. Implement UI specification above in ui.cpp. Two registry entries only: console + details. All navigation/dots use registry count, easy later static view registration. Keep original detailed dashboard render sections intact.
2. Fix cache bug in model.cpp: when an old window absent from a present account is appended, age its reset by elapsed (currently d.w[wi]=ow bypasses age). Cached OpenRouter numbers must remain VISIBLE even when orOk false: renderer checks whether any cached numbers exist, shows them plus short stale/error indicator rather than hiding them. Do not fake clean status.
3. Reset credits: service currently omits rc when zero, but caching now preserves omitted rc; emit rc for any known nonnegative reset_credits including 0. Adjust existing test expectation for zero, no additional test suite. No changes elsewhere.
4. Update UI docs concisely: exactly two views, chosen urgent window, freshness, palette/config, where Claude edits later. No long report.

## Constraints and stopping condition
No delegation, no flash, no COM6/service access, no commits/tags/push. Stay inside files list. One focused implementation, one build and diff check; do not repeatedly polish or explore unrelated edge cases. Capture build log to build/. If a required out-of-scope change arises report it. Parent performs final runtime screenshot and review. Return concise changed-files + build results and stop.
