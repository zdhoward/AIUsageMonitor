---
id: T-005
title: Replace cluttered quota bars with session and weekly rings
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
User finds the current console too cluttered. Replace its progress bars with two circular progress rings per provider, Session on the LEFT and Weekly on the RIGHT, each labeled and containing exact % remaining. Rings are the primary glanceable information. Reset details are muted gray in a tidy table under the provider title. Exactly two views; original details view unchanged. Landscape rotation1 stays default. No service/model changes, additional stats, or tests.

## Design and implementation
Actual display is 320x240 landscape, 240x320 portrait; framebuffer RGB332, TFT_eSPI. Keep current dark palette, session ring capacity-warning colors, weekly ring YELLOW from user preference. Render percent remaining (never used), correct5h/7d identity, realzero vsunknown, RAM-cached values/stale status, quiet easing. No constant animation/pulsing on new view. Reuse helper text/formatting/easing.

For landscape keep three horizontal provider rows (about65px high). Recommended layout: left column x10..135 for title + muted two-row reset table, two rings side by side in right region centered around x183 and x267, radius21..23, 4px stroke. Percent centered inside (font2), Session/Weekly labels below (font1 or2 if fits). Main title font2 left. Reset table muted gray, compact separate `Session` and `Weekly` entries with unambiguous values like `S reset 1h10m`, `W reset 4d20h`, `due`/`--` when needed. Avoid bright text dominating rings; gray numeric text in table. Remove the old giant top-right session percentage and bars entirely, redundant CL1/CL2/Codex identifiers can go (titles CLAUDE A/B/CODEX suffice). The ring outline+center number is the focal point. Font2 reset labels may need compact labeling to fit left column; do NOT overlap ring region. Portrait uses the taller row space to keep both rings side by side and muted reset table below title; derive coordinates from W/H. Header/footer quiet and short, retain truthful updated age / stale indication without duplicating STALE everywhere. A small per-row stale badge is okay if not colliding.

Use TFT_eSPI arc drawing if available in installed library, or bounded line-segment arcs only if needed; inspect API first. Ring fill tracks remaining fraction clockwise from12o'clock, underlying subdued track visible. For unknown render track/dashes with --, never fakezero. For real0 render empty track and0%. Full100 fullring. Round easing to ring angle; percentages exact. Prefer simple helper e.g.drawQuotaRing. Do not import libraries or add complex abstractions.

FW_VERSION1.4.0. Update concise UI docs for ring layout/mapping and muted resets. One focused pass and one build; no flash/COM6/service, no delegation, commits, tags, publishing. Parent reviews and flashes. Save build output to build/build.log. Finish promptly with concise results.
