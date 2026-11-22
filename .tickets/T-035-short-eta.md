---
id: T-035
title: White 5h reset ETA within thirty minutes
task_type: feature
lane: implement
critical: false
test_phase: request_complete
paid_fallback: false
attempt_limit: 2
direct_paid_token_estimate: unknown
files:
  - firmware/AIUsageMonitor/ui.cpp
acceptance:
  - git diff --check
---

## Goal
Single-file mechanical implementation: reset countdown TEXT ONLY turns TFT_WHITE
for a known 5h window whose remaining ETA is between 0 and 1800 seconds inclusive.
Unknown and expired deadlines must not turn white. Preserve existing weeklySoon
behavior and percentage/ring colors. Inspect drawGridLine (used by Console/Proxy)
and any other 5h ETA render path. Antigravity multi layout does not show a 5h ETA,
so do not introduce one. Use parent for architectural decisions.

## Dispatch checkpoint
- Owner requests Neon test; fully specified, non-critical single-file pilot.
- Exact medium model probe returned HTTP200/OK in 2.2s immediately before launch.
- Requested codex_proxy_gemini/gemini-4-neon-xhigh(medium), medium/default.
- Previous T-034 agent route failed 429 before code; this is a new owner-directed
  setup recovery task, not a hidden retry. No paid fallback or extra agents.

## Scope and budget
Only ui.cpp. No commits, credentials, service/config/docs edits, network probes,
build, flash, full suite or agents. One bounded implementation. Parent reviews,
builds and captures 30m boundary, >30m, expired and unknown using real hardware.
Run git diff --check only and report exact changed function/condition and actual
model/session settings if exposed. Use apply_patch. Stop after returning patch.
