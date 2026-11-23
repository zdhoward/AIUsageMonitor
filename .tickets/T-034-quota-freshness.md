---
id: T-034
title: Preserve quota observation age and expose failed refreshes
task_type: bugfix
lane: implement
critical: false
test_phase: request_complete
paid_fallback: false
attempt_limit: 2
direct_paid_token_estimate: unknown
files:
  - service/aimon/sources/cpamc.py
  - service/tests/test_cpamc_freshness.py
acceptance:
  - python -m unittest discover -s service/tests -p test_cpamc_freshness.py
---

## Goal
Implement the fully specified collector side of quota freshness. Work on the
existing my-setup branch, no commits, no publication, no service restarts,
no firmware/config changes, no additional delegates. Parent owns integration.

## Dispatch checkpoint
- Existing reproduction: build/check_proxy_stale_signal.py exits 1 on b974e45:
  two-hour-old cached 100% plus failed quota probe produces up=1, age=0, attn=0.
- Owner explicitly requests Neon as an organic implementation pilot.
- Target codex_proxy_gemini/gemini-4-neon-xhigh(medium), reasoningEffort medium,
  serviceTier default; canonical identity codex_proxy_gemini/gemini-4-neon-medium.
- Previous live Neon request succeeded, no model cooldowns in current telemetry;
  old model-scoped exhausted overlay is stale setup evidence, not a new failure.
- Attempt 1 of 2; no paid fallback. Parent reviews independently.

## Contract and ordered steps
1. Write focused offline unittest regressions first; demonstrate the pre-fix
   failure, then implement only cpamc.py. No live external calls or full suite.
2. Track per-account successful live quota observation in entry checked_at
   (epoch seconds); update only after a successful nonempty complete windows
   probe. _live_at remains attempt cadence. Preserve last good windows AND
   checked_at for every failure including 401/403. Carry latest auth_failed
   and probe_ok=False on retained results. Successful retry clears failure.
   Capture success time after the request finishes, not poll-start time.
   If any required profile window is missing, treat response as failed rather
   than stamping partly retained/missing data fresh. skip_if disabled remains
   optional and should not cause missing-window failure.
3. Add QUOTA_STALE_S = LIVE_EVERY_S + 60 (360 seconds). pool_groups emits
   group age: oldest successful quota age among active accounts, -1 if any
   has no known observation; st:1 when any account lacks a successful probe,
   last attempt failed, or successful observation is older than QUOTA_STALE_S.
   Ignore disabled/hidden accounts. For groups without a live request profile,
   retain current unknown behavior; do not imply their headers were probed.
   Existing a/attn must warn when st so old firmware doesn't stay green.
4. line() preserves existing account-list age/up semantics and emits qa (oldest
   visible group quota age, -1 if unknown) and qs (any group stale, 0/1).
   Unknown observation is not zero age. Repeated successful auth-files polls
   cannot renew checked_at. Time-only staleness must work even with no new poll.
   Missing account-list access retains quota ages, marks link down; a successful
   account-list retry alone never clears a failed quota probe. Account removal
   must remove its freshness contribution. No IDs/emails/secrets in payloads.
5. Add safe status via line() only; parent will expose this in health/status.
   Keep payload below existing 4095-byte limit and preserve q trimming behavior.

## Three acceptance criteria
- Failed quota probe after success retains numbers and original checked_at,
  flags group/global stale+attention, and age grows despite account-list success.
- Recovery clears stale after a real success; mixed accounts use oldest age;
  startup unknown, auth failure, overdue/hung polling, missing required bucket,
  and disabled/removed accounts have focused offline coverage.
- Focused test command passes, existing source interface remains compatible,
  no unrelated changes. Report exact commands, failures before fix, findings,
  changed paths, requested/observed model settings and available session IDs.

## Budget and stop condition
One red run and one green focused unittest run; rerun only on relevant changes.
At most two implementation attempts. No broader suites or live requests.
Return patch and receipt. Do not edit tasks, ledger or other files: parent will
log every tracked edit. Stop after reporting; no additional agents or servers.
