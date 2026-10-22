---
id: T-006
title: Reset labels below rings and shared quota column headings
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
Final small UI refinement requested by user: ring captions should be time until next reset instead of repeated Session/Weekly. Leave the data-table area under provider titles EMPTY. Header title becomes `AI USAGE (3 CLIENTS)` aligned left; put Session and Weekly column headings above their respective ring columns. Keep ring geometry/colors/easing/cache, exactly two views, original details view, and default landscape rotation1.

## Implementation
Read ui.cpp drawQuotaRing/drawClientCard/drawConsole. Remove reset-table construction/draw entirely (no replacement stats). At each drawQuotaRing call build a short caption from that window.r minus elapsed: `38m`, `2d12h`, `due` if0, `--` ifunavailable. Caption below that ring in muted gray, using existing label parameter. Exact percentage inside ring unchanged.
Header space: landscape title font2 at x10,y4 currently cannot fit title plus both column headers at font2 on one row. Use compact font1 for combined title if needed (text width126 for21chars fits left area x10..145); Session/Weekly centered at ringx183/x267 on the SAME header row (font1 or2 as fits), divider22; don't consume extra vertical ring space. User explicitly wants title+client count on left and headings above ring columns. Position title/header from same reusable ring-center layout math used by drawClientCard, so headers actually align with centers. In portrait do a separate title row and column-header row if necessary, current top30 may need top40 and smaller gap/row height while keeping visible tracks/captions. Do not squeeze labels into provider row or reintroduce table data. No extra layout framework.
FW_VERSION1.4.1. Update short UI docs to reflect empty reserved data area and new headings/captions.

## Constraints
Small scoped task; no research/test expansion. One build, diffcheck; no agents, COM6/flash/service, commits, tags, publishing. Finish promptly with actual changed files and acceptance results. Do not stop after saying you'll implement. Build log to build/build.log.
