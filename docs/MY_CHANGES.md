# My changes

| File | What and why | Date |
| --- | --- | --- |
| scripts/attribution_guard.py | Reject AI attribution at commit and push; prepare verified history cleanup. | 2026-11-21 |
| .github/workflows/attribution.yml | Audit history in CI to catch attribution from other clones and merges. | 2026-11-21 |
| docs/recipes/contributor-attribution.md | Document safeguards and safe historical cleanup. | 2026-11-21 |
| docs/recipes/README.md | Index the attribution maintenance recipe. | 2026-11-21 |
| tasks/todo.md | Record contributor cleanup plan and verification. | 2026-11-21 |
| tasks/lessons.md | Record the recurring AI credit problem and prevention. | 2026-11-21 |
| docs/MY_CHANGES.md | Track this maintenance change. | 2026-11-21 |
| scripts/service.ps1 | Remove a machine path from the scheduled-task description so the privacy guard permits publication. | 2026-11-21 |
| HANDOFF.md | Record published cleanup, validation, backup and continuation; retain earlier backlog. | 2026-11-21 |
| docs/PROJECT_LOG.md | Record cleanup outcome and retrospective. | 2026-11-21 |
| tasks/todo.md | Plan and record the requested Antigravity live reliability check. | 2026-11-22 |
| docs/MY_CHANGES.md | Track the live-check documentation. | 2026-11-22 |
| .tickets/T-034-quota-freshness.md | Specify the bounded Neon collector pilot and freshness contract. | 2026-11-22 |
| service/aimon/sources/cpamc.py | Separate quota observation age from connection polling, retain failed readings as stale, and isolate parser failures per account. | 2026-11-22 |
| service/aimon/server.py | Expose safe proxy freshness and quota failure in health/status. | 2026-11-22 |
| service/aimon/profiles/antigravity.json | Keep daily quota authority on failure; allow genuinely optional third-party/Argon buckets. | 2026-11-22 |
| service/aimon/profiles/claude.json | Allow plans without a weekly window. | 2026-11-22 |
| service/aimon/profiles/codex.json | Allow valid single-window Free plans. | 2026-11-22 |
| service/tests/test_cpamc_freshness.py | Cover retained observations, failure/recovery, parser isolation, plans, age and health. | 2026-11-22 |
| firmware/AIUsageMonitor/model.h | Store separate proxy/group quota freshness with legacy compatibility. | 2026-11-22 |
| firmware/AIUsageMonitor/model.cpp | Parse optional quota age and stale fields. | 2026-11-22 |
| firmware/AIUsageMonitor/ui.cpp | Show STALE and true quota age, including independent aging after the stream stops. | 2026-11-22 |
| profiles/my.json | Preserve the installed default layout on the personal branch when rebuilding. | 2026-11-22 |
| docs/PROTOCOL.md | Document freshness fields, failure retention, health and optional windows. | 2026-11-22 |
| tasks/lessons.md | Record the correction that connection activity cannot establish fresh quota. | 2026-11-22 |
| tasks/todo.md | Record implementation, verification and Neon pilot outcome. | 2026-11-22 |
| HANDOFF.md | Record installed freshness behavior, evidence and pilot limitations. | 2026-11-22 |
| docs/PROJECT_LOG.md | Record the verified fix and blocked Neon attempt. | 2026-11-22 |
| .tickets/T-035-short-eta.md | Specify the bounded Neon ETA task and boundary behavior. | 2026-11-22 |
| .tickets/T-036-claude-reset-parser.md | Specify read-only Claude reset inventory parser and pilot. | 2026-11-22 |
| service/aimon/sources/claude_resets.py | Parse usable reset count and earliest known expiry without identifiers. | 2026-11-22 |
| service/aimon/profiles/claude.json | Request the opt-in read-only reset inventory with usage. | 2026-11-22 |
| service/aimon/sources/cpamc.py | Wire Claude inventory into existing per-account reset count/expiry payload. | 2026-11-22 |
| service/tests/test_claude_resets.py | Cover inventory schema, unknown/zero and expiry boundaries. | 2026-11-22 |
| service/tests/test_cpamc_freshness.py | Verify inventory integration and unknown counts without affecting quota. | 2026-11-22 |
| firmware/AIUsageMonitor/ui.cpp | Highlight short 5h ETA, prioritize credit expiry and retain visible overflow reminders. | 2026-11-22 |
| scripts/cpamc_callback_bridge.py | Forward only local Claude/Codex final OAuth callback hops to configured CPAMC. | 2026-11-22 |
| scripts/cpamc-callback-bridge.ps1 | Install/remove the headless limited-user callback bridge logon task. | 2026-11-22 |
| service/tests/test_cpamc_callback_bridge.py | Verify loopback/path isolation, query privacy, no redirects and invalid-target health. | 2026-11-22 |
| docs/CPAMC_LOGIN.md | Explain provider versus management redirects, installed workaround and Neon evidence. | 2026-11-22 |
| docs/CPAMC_HOME.md | Link current setup/callback and reset-credit behavior. | 2026-11-22 |
| docs/PROTOCOL.md | Document Claude rc/rx and short ETA/expiry indicators. | 2026-11-22 |
| tasks/todo.md | Record supported behavior, exact live results and setup findings. | 2026-11-22 |
| tasks/lessons.md | Record workload-specific Neon checks and separate callback authority. | 2026-11-22 |
| HANDOFF.md | Record installed credits/ETA/callback behavior and explicit validation limits. | 2026-11-22 |
| docs/PROJECT_LOG.md | Record display verification, CPAMC update and bounded Neon failures. | 2026-11-22 |
| .tickets/T-037-neon-setup-check.md | Specify real tool-agent acceptance of the supported isolated Neon client configuration. | 2026-11-22 |
| tasks/lessons.md | Record the owner's correction to start from the documented standard integration. | 2026-11-22 |
| tasks/todo.md | Track supported Neon setup and actual acceptance evidence. | 2026-11-22 |
| docs/CPAMC_LOGIN.md | Replace quota guesses with documented client configuration and bounded evidence. | 2026-11-22 |
| scripts/check_neon_setup.py | Neon-authored read-only setup checker; parent clarified structural-rule validation wording. | 2026-11-22 |
| HANDOFF.md | Record verified supported Neon configuration, cached-process restart and acceptance limits. | 2026-11-22 |
| docs/PROJECT_LOG.md | Record accepted real Neon task and owner's process correction. | 2026-11-22 |
| HANDOFF.md | Reconcile routing policy, live health, sync, publication and remaining validation limits at wrapup. | 2026-11-22 |
| tasks/todo.md | Record wrapup checks and branch publication tracking. | 2026-11-22 |
| docs/PROJECT_LOG.md | Record wrapup and evidence-based retrospective. | 2026-11-22 |
| scripts/service.ps1 | Add a 5-minute watchdog trigger (IgnoreNew) so the service returns after an outside kill. | 2026-11-22 |
| tasks/lessons.md | Record how the service was killed by another session and how to trace it. | 2026-11-22 |
| HANDOFF.md, docs/PROJECT_LOG.md, tasks/todo.md | Record the service-kill cause, watchdog, magi sync and branch merge. | 2026-11-23 |
