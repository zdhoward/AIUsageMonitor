---
id: T-004
title: Separate session and weekly bars with explicit reset labels
task_type: feature
lane: implement
critical: false
files:
  - firmware/AIUsageMonitor/ui.cpp
  - firmware/AIUsageMonitor/config.h
  - docs/UI.md
  - docs/UI_HANDOFF.md
acceptance:
  - powershell -NoProfile -File scripts/build.ps1
  - git diff --check
---

## Goal
Small UI refinement, not a redesign. User says almost perfect, wants weekly usage as another bar UNDER session usage and unambiguous session vs weekly reset times. Exactly two views retained; default landscape rotation1 remains. No service/model changes or new tests.

## Implementation
1. In drawClientCard choose session by label `5h`, weekly by `7d`, not most urgent. Session always first/main percentage; weekly underneath with its own percent, bar and explicit reset. Preserve remaining-capacity semantics, independent warning colors, easing, unknown `--`, cached/stale handling. If a window isn't reported, show its bar unknown and reset unavailable (don't relabel an arbitrary quota). Reuse existing leftBar/text/formatting.
2. Fit actual 320x240 landscape with larger rows by tightening header/footer whitespace. Suggested geometry: header y4..20, divider22, top24, footer y222, cards about64px tall with2px gaps. Card name and large session percentage at top; session reset line y+24 (font2), session bar y+40 height3; weekly percentage and reset line y+44 (font2), weekly bar y+61 height3. Ensure reset strings don't collide with the large session percentage; names remain stable CLAUDE A/B/CODEX. Examples `Session reset 1h48m` and `Weekly 53% reset 4d21h`, but can abbreviate reset to clear labelled `Session: 1h48m` / `Weekly 53%: 4d21h` if needed. Both windows' reset semantics must be explicit, including update due/unavailable. Never put reset text over a bar. In portrait use extra vertical space for comfortable spacing. Footer updated age and health stay visible, dots don't overlap. Keep existing dark palette and entire original detailed view unchanged.
3. FW_VERSION1.3.3, update concise UI docs removing outdated most-urgent-window description. Keep brightness/rotation config unchanged.

## Constraints
Implement promptly in one pass. One build, diff check, stop. No agents, no flash/COM6/service, no commits or publication. Build output in build/build.log. Parent reviews and flashes. Report changed files and acceptance only.
