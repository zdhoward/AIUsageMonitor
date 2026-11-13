# Catchup ledger (2026-11-13)

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
