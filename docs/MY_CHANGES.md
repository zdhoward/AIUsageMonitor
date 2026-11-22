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
