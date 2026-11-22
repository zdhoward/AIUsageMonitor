# Catchup ledger (2026-11-13)

## Reset credits, short 5h ETA and CPAMC setup (2026-11-22)

- [x] Verify Claude banked-reset count/expiry sources without consuming a reset.
- [x] Make known 5h reset ETAs white at 0..1800 seconds; inspect boundary frames.
- [x] Test exact Neon medium agent route, diagnose 429/update relevance and callback authority.
- [x] Review, build/flash and verify supported changes; record findings and limits.

Claude's read-only usage request needs cedar_ember=1. Four live accounts returned
eligible:false and an empty grants list; counts currently zero. Wired parser to
rc/rx with unknown=-1, no identifiers and no consumption. Known earliest expiry
stays visible even if another grant lacks a date. The Messages card sorts expiry,
preserves its first account row under overflow and shows white near-expiry text.
Unknown inventory says Unavailable; expired cached inventory prompts check.

Verification: 11 parser +18 freshness/integration +2 prior credit checks passed.
Built/flashed with hash verification; initial COM6 busy resolved by stopping the
service during flashing and restarting afterward. Inspected real framebuffer
fixtures at30m white,31m muted,unknown muted,expired muted; six-credit overflow
showed the earliest Claude expiry with +5 in the heading. Restored healthy live
feed with Claude rc=[0,0,0,0]. Evidence: build/reset-eta-*.png and build/reset-eta-
{build,flash}.log. Sonnet parser independently reviewed/refined by parent Sol;
Sonnet static UI/integration review found0 Important; nits addressed where useful.

Neon exact-medium tiny chat succeeded on CPAMC8.1.0 and8.1.1, but an organic ETA
agent task failed429 before code, and one post-update parser task also failed429.
Proxy logs show upstream RESOURCE_EXHAUSTED. No quality pass and no repeated
probes. Official existing updater installed8.1.1 after a temporary replacement
PermissionError; authenticated backend/UI checks passed, updater now current.
No credentials, billing or provider redirects changed. Router/pilot receipts
record failures and established-model rescue separately; usage costs UNKNOWN.

Claude/Codex callback investigation confirmed a hardcoded127.0.0.1 final management
hop while CPAMC listens only on Tailscale. Installed a loopback-only callback
bridge as a limited-user headless logon task. Only the two fixed callback paths
are forwarded; no management API, client auth/cookies, redirects, query logging
or code storage. Offline fake-upstream tests and local health/listener checks
verify forwarding; no real account login was initiated. Another-device browser
still uses the management page's callback-URL input. Details: docs/CPAMC_LOGIN.md.

Reflection: tiny replies did not predict the full Responses/tool workload. Two
bounded owner-requested pilots were enough to establish continued unavailability;
no output means no code-quality verdict. Delegated parser/bridge implementation
and reviews; coordinator retained architecture, small review fixes and runtime
verification. Native read-only discovery was unavailable (unknown model) and
completed inline. No public push, release or new provider account action.

## Quota stale warning fix / Neon pilot (2026-11-22)

- [x] Implement separate successful-quota age and failed/overdue status with focused offline regressions (Neon attempt failed 429; coordinator implemented).
- [x] Review collector patch; add visible group STALE, quota-age footer, and proxy health/status.
- [x] Verify failure and recovery on hardware; build/flash, capture and inspect frames; record pilot review and outcome.

Outcome: 16 focused freshness tests and 13 existing Proxy tests passed. Original
two-hour-old cached-value repro now warns. Independent Sonnet and native reviews
caught optional-plan handling and per-account parser exception isolation; both
were corrected and covered. The final suggestion to exempt unprobeable sources
was declined: unknown quota must remain visibly unverified. Daily-only Antigravity
authority is intentional; a different endpoint must not hide a failed refresh.

Firmware built with the personal profile, flashed with hash verification, and
service restarted. Inspected landscape/portrait failure frames and recovered/live
frames. An offline failure using real anonymous display values yielded qa=900,
qs=1 and STALE badges; recovery yielded qa=0, qs=0 with identical quota values.
Live health reports actual quota age independently of account polls and USB ACKs.
One framebuffer transfer was short; recapture with a settle interval succeeded.
Evidence: build/quota-stale-landscape.png, quota-stale-portrait.png,
quota-recovered.png, quota-live-final.png and quota-freshness-{build,flash}.log.

Neon pilot: exact medium agent route failed at T3's retry limit with HTTP 429,
before patch/reply/tool execution. No model code exists to review and no quality
pass is claimed. Availability attempt recorded (BLOCKED), exact raw IDs retained
locally, missing usage/serving settings UNKNOWN. Coordinator rescue and review
disposition recorded separately; global pilot notes/availability overlay updated.
No retry loops, credentials changed, release/tag or public push. Temporary
verification and small review fixes stayed inline; firmware was delegated and
two independent reviews were used. Reflection: a tiny high-route reply proves
neither the exact medium route nor sustained tool-agent readiness.


## Antigravity live check (2026-11-22)

- [x] Capture the running display and USB/service baseline without restarting it.
- [x] Compare daily-endpoint quota and CPAMC cooldowns per account; observe at least twelve minutes of refreshes and USB acknowledgements.
- [x] Capture the final framebuffer and record results and any unresolved limits.

Result: 720 seconds, 25 samples, zero unplanned failures. One expected serial
pause during the midpoint screenshot made the strict harness exit 1; its only
failed sample has paused=true. USB ACK age otherwise stayed at or below 4.8s.
Three per-account quota-probe rounds succeeded; four distinct direct-collector
check timestamps were observed. Additional daily-only snapshots returned 200
for both accounts, with no cooldowns. Initial, midpoint and final framebuffers
were inspected: Neon 5h/7d 100%, shared Claude 5h 100% / 7d 75%, Argon 7d 100%.
The reported ten-minute outage did not recur during this observation window.

Checks completed while observing: real Neon and Argon requests returned HTTP 200
and the requested reply. Fresh daily-endpoint readings matched the framebuffer;
the tiny request usage appeared upstream but rounds to 100% on the display.
The monitor's local API key returned 401; the existing Codex proxy key succeeded.
Quota collection uses the separate working management key. No credentials changed.

Reliability finding: an offline reproduction of a failed live quota probe with
two-hour-old cached 100% quota still produces proxy up=1, age=0, attn=0 after
successful account-list polling. Health/ACK success alone cannot prove fresh
Proxy quota. Independent read-only review confirmed this and the possibility
of falling back from daily to a primary endpoint with different quota.
This is a demonstrated diagnostic gap, not a reproduced live ten-minute outage.
Production code and firmware remain unchanged for this requested live check.
Evidence scripts and redacted results are local under build/antigravity-* and
build/check_*; no full suite, build or flash was needed. Temporary check scripts
were kept inline because they only collect bounded diagnostic evidence; the
quota reliability review was delegated independently.


## Contributor attribution cleanup (2026-11-21)

- [x] Inspect live GitHub contributors and historical attribution: API lists only
  the owner, but 124 reachable commits contain AI co-author trailers.
- [x] Install commit and push checks, preserving the existing public push guard.
- [x] Verify rejection of AI credits and acceptance of human credits.
- [x] Prepare a separate clean-history branch and prove file trees unchanged.
- [x] Obtain explicit approval and publish with an exact force-with-lease.
  Align local main and my-setup with the clean history.

Verification: the installed commit-msg hook rejected the AI fixture (exit 1)
and accepted a human fixture (exit 0). The push handler rejected the original
history and accepted the cleaned 207-commit history; chained-hook stdin and
failure propagation passed. Reinstallation preserved the original public push
guard. The attribution-only variant has an identical tree; all rewritten objects were
verified. Doctor passed required checks. No firmware build, flash, or application
suite was run because this change only affects Git metadata and safeguards.

Publication: owner approved on 2026-11-21. Replaced remote main with cleaned
history using an exact force-with-lease; both push guards passed. GitHub's
attribution workflow passed on the published head, and the contributor API
lists only the owner. Original refs are backed up in the local ignored bundle
`build/attribution-before.bundle`.
- [x] Retag (owner approved): all 27 tags moved to their clean twins, AI
  trailers removed from tag messages, and the 18 published tags force-pushed with
  exact leases. Remote tags match local; 6 releases remain attached. Backup:
  `build/tags-before-retag.bundle`.
Other clones must resync before contributing; the history audit rejects an
incoming branch that restores AI credits.
The publication privacy check found historical machine paths in setup notes
and a current scheduled-task description. A second prepared branch redacts
those paths; its current-file diff was limited to that description. This
privacy-safe variant passed the publication guard and is the published history.
Wrap-up: no open PRs, successful attribution CI on 2ffac7a. Current handoff is
HANDOFF.md; release tags since moved to the clean history.
- [x] Consolidate (owner request): the owner checkout keeps only `main`.
  Deleted my-setup and the attribution-* branches after confirming their work
  was on main. Published the 9 local-only tags, so all 27 match GitHub.
  Attribution CI passed on 1af529d.

Sources: HANDOFF.md, tasks/lessons.md, .tickets/*, `gh issue list` (none open), TODO/FIXME grep (none), `git worktree list`, live CPAMC `auth-files` (read-only). No DECISIONS.md exists; GOALS.md and docs hold no answers for the owner items below.

## auto
| # | Item | Source | Result |
|---|---|---|---|
| A1 | Remove the stale `t3/*` worktrees and branches (was O10) | todo O10 | Done. 28 of 29 branches were merged (ancestor of `main`, or every commit subject is on `main`); `t3/optional-pages-screensaver` is a superseded Oct 23 draft that is still on `origin`. Before removal: bundle of all 29 branches plus 13 uncommitted-diff patches saved to a sibling backup folder (bundle verified; deleted 2026-11-13 on the owner's say-so). Only `main` remains. |
| A2 | Confirm GPM's CPAMC priority changes | HANDOFF 2026-11-10/11-12 | Done (read-only). Every active account has a priority: Antigravity 20/10, Claude 40/30/20/10, Codex 20/10, xAI 10. |
| A3 | Unit test for `cpamc.load_base` (env > `.cpamc.env` > default) | HANDOFF 2026-11-12 | Done: `ProxyAddressTests` in `service/tests/test_service.py`. Compiles; not run (deferred). |
| A4 | `add-card.md` small-model gap test (was B5) | HANDOFF 2026-11-06 | Done. Haiku followed steps 1-4 in an isolated worktree; build ok (34% flash), not flashed. Gaps fixed in `add-card.md` (prerequisites line, ~20-line model card, full two-row sample, `build ok` is not the last line, missing-profile hint) and `customise-safely.md` step 3 (exit 0 check, art warnings expected, unchanged copy valid). Test worktree removed. |

## Dropped (stale notes, checked)
- HEALTH hook still probing `127.0.0.1:8317`: already fixed. `~/.agents/model-router/scripts/doctor.py` probes the Tailscale address (Home Repo catchup 2026-11-12).
- O6 P-Gemini default model: the 2026-11-10 handoff verified P-Gemini working on `gemini-3.8-flash-high`; that config lives outside this repo.

## owner
| # | Item | Needed |
|---|---|---|
| O4 | One Claude account (the third in display order) reads 7d 0% and 5h 0% from Anthropic's headers; the owner says all accounts look fine but can't tell which is which | owner: check that account in `/usage`; if it has quota left, report it and the parser gets investigated |
| O9 | Console Antigrav/Argon cards read T3's stored Google login (a different account), so they stay 5h-only; the Proxy home page already shows the right numbers from CPAMC | owner: keep Console as is (default), or ask to switch its source to CPAMC |

## Answered 2026-11-13 (see GOALS.md "Owner answers")
- O1 keep the account count; O2 no next provider (T-033 closed).
- O3 done: Gemini Flash ran the README setup prompt on a clean clone up to the build (build ok, doctor all OK on `my-setup`; flash, service and logon task skipped). Its 7 gaps are fixed: proxy setup (`.cpamc.env`) in SETUP.md and the prompt, arduino-cli via Arduino IDE 2, board confirmation asked, System/companion map to `pages`, doctor FAIL on `main` documented as expected, doctor now checks Python packages.
- O5 done: any quota left shows at least 1% (`cpamc._pct`, commit `4d6bb60`, service restarted); `ProxyPercentTests` added, not run.
- O7 done: README trimmed (commit `15f753a`).
- O8 policy: patches ship on `main` with no tag; minor versions get a tag and a release. No release needed now.
- O11 no change. O12 done: both backup folders deleted (all art verified present in `assets/`) and the remote draft branch deleted.

## blocked
| # | Item | Blocker |
|---|---|---|
| B1 | Updates tab update-available and conflict panels untested | needs the next minor release (patches carry no tag) |
| B2 | Resize recipe on a non-320x240 board | needs that hardware |
| B6 | Backlog tickets T-018 audio visualizer, T-019 stock ticker, T-026 weather, T-008/T-009 MINT | feature work the owner has not scheduled |

## Assumptions
- No frontload questions: every auto item was specified by the repo notes.
- Testing rule: no suites run; `ProxyAddressTests`, `ProxyCooldownTests` and `ProxyResetCreditTests` are written and unrun.
- Owner rule "deleting merged worktrees is never an ask" covers the worktree cleanup. The backup bundle and the remote draft branch were later deleted on the owner's say-so (O12).
- The add-card test stops at the build: flashing would replace the owner's running firmware with a test card.
