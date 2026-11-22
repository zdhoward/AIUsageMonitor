---
id: T-036
title: Read Claude reset inventory without consuming grants
task_type: feature
lane: implement
critical: false
test_phase: request_complete
paid_fallback: false
attempt_limit: 1
direct_paid_token_estimate: unknown
files:
  - service/aimon/sources/claude_resets.py
  - service/tests/test_claude_resets.py
acceptance:
  - python -m unittest discover -s service/tests -p test_claude_resets.py
---

## Goal
Implement a pure function parse_inventory(block, now) -> dict with only rc
(available reset count) and rx (earliest expiry epoch, 0 unknown). Parent wires
the function to CPAMC and profile. Allowed paths exactly the two above.

## Dispatch checkpoint
Owner requests Neon test and Claude reset inventory. Fully specified single
module non-critical parser. Previous agent failed 429 before patch on CPAMC8.1.0.
Backend now official checksum-verified8.1.1; exact medium chat probe200/OK.
One post-update agent attempt codex_proxy_gemini/gemini-4-neon-xhigh(medium),
medium/default. No fallback, extra agents, commits or production restart.

## Exact contract
- block is the `cedar_ember` JSON object from GET /api/oauth/usage?cedar_ember=1.
  Reference: build/claudeResetCredits.ts public T3 implementation; live responses
  on four accounts currently eligible:false, grants:[], next_grant_id:null.
- Unknown/missing/malformed block or non-list grants -> {rc:-1,rx:0}; do not
  report zero for unreadable data. Explicit eligible:false with empty grants is
  known zero. eligible must be boolean. Unknown eligible -> unknown result.
- eligible:true -> grants must be list. Each grant has resets_left nonnegative
  int (bool invalid), usable_now boolean, optional paused bool, optional ends_at
  RFC3339 timestamp with explicit timezone. Sum positive resets_left only when
  usable_now is True, paused is not True, and expiry absent/null or >now.
  Ignore expired, paused, exhausted and not-usable grants. Unknown/malformed
  grant must make whole inventory unknown (avoid falsely claiming zero).
- rx is min positive known future expiry among counted grants; rx=0 if none
  has a known expiry. Unknown expiry must not hide a known imminent expiry.
- Validate timestamp, do not accept timezone-free/date-only strings or NaN.
  Invalid ends_at -> unknown inventory. No request or identifier fields returned.
- If eligible:false and grants nonempty -> {rc:-1,rx:0} conservative ambiguity.
- No network, credentials, reset/consume endpoint, other files, commits, agents,
  build/flash or service modifications. Use stdlib only.

## Validation budget
Focused offline tests cover valid count/soonest expiry, empty, expired/paused/
not-usable, missing block, invalid count/date/type, unknown expiry and ineligible.
One focused run, rerun only for relevant corrections. Report actual identity and
exact test output. Stop after patch. Parent independently reviews/integrates.
