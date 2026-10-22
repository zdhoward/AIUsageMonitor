---
id: T-002
title: Finish cached display state and extensible portrait views
task_type: feature
lane: implement
critical: false
files:
  - firmware/AIUsageMonitor/model.cpp
  - firmware/AIUsageMonitor/ui.cpp
  - firmware/AIUsageMonitor/ui.h
  - docs/UI.md
  - docs/UI_HANDOFF.md
acceptance:
  - powershell -NoProfile -File scripts/build.ps1
  - git diff --check
---

## Goal
Complete the user's original display request: retain latest known displayed values through unavailable data, and make tap-cycled views easy to extend. Keep current portrait rotation 0 and the clean quota/reset design. No extra features or elaborate tests.

## Context
Current commit v1.2.0 already implements bright quota caching, account focus pages, CST820 tap/release, and easing. Parent implemented it before following the routing preference; you are doing remaining bounded implementation. User wants a slick readable 240x320 display below their monitor and future Claude UI edits to be easy. Read docs/UI.md. No browser app; real TFT_eSPI firmware. Parent alone flashes and owns COM6/service. Do not spawn agents. Do not change files outside the list. Do not publish, tag, or commit. Build output goes to build/; capture verbose logs there and report only summary.

## Steps
1. In model.cpp preserve last known section values when incoming sections are absent/unavailable: activity, subscription usage/sparkline/by-account, free provider stats, NIM, and OpenRouter. Valid explicit zero must replace a cached number. Preserve account metadata (color/plan/reset credits) when the corresponding field is absent, including quota windows already cached by identity. A reset credit explicit zero must clear it. Keep exact quotas, no fake refills. Missing data must remain unknown when no previous measurement exists. Preserve current status/error flags so stale/error information is not concealed. Relative activity times must account for elapsed time if retaining activity. Avoid refreshing age/reset countdowns merely by replaying missing fields. Update cached peak summary from retained windows rather than blanking it when hi is absent; clearly name it as cached if necessary, do not imply fresh status.
2. In ui.cpp replace implicit scattered m.nacc+2 arithmetic with a small view descriptor/registry using render callbacks (overview, generated account focus instances, details). A future static view should need one registration entry plus a renderer; navigation, dispatch, and pagination dots derive from that list. Avoid a framework. Retain current selected account by identity on reorder; safely fall back on invalid selection. Keep touch action uiNextView and serial !NEXT public behavior unchanged.
3. Fix overview layout's existing four-account overflow without shrinking it to unreadable text: use two overview pages when more than three accounts, with pages as descriptors in the same view list. Keep the normal three-account appearance. Ensure focus reset text with 3 windows doesn't overlap the next window. Preserve the exact numeric labels with bar interpolation and full brightness cached values.
4. Update docs/UI.md and UI_HANDOFF.md with accurate extension points/cache behavior, short entries only. No test suite additions: compile and inspect diff. Report risks and exact files changed. Parent does runtime/screenshots.

## Done when
Both acceptance commands exit 0, all changes stay within allowed files, and the implementation report explains cache fallback vs explicit zero and how to register a future view.
