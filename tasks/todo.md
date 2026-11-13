# Catchup ledger (2026-11-13)

Sources: HANDOFF.md, tasks/lessons.md, .tickets/*, `gh issue list` (none open), TODO/FIXME grep (none), `git worktree list`, live CPAMC `auth-files` (read-only). No DECISIONS.md exists; GOALS.md and docs hold no answers for the owner items below.

## auto
| # | Item | Source | Result |
|---|---|---|---|
| A1 | Remove the stale `t3/*` worktrees and branches (was O10) | todo O10 | Done. 28 of 29 branches were merged (ancestor of `main`, or every commit subject is on `main`); `t3/optional-pages-screensaver` is a superseded Oct 23 draft that is still on `origin`. Before removal: bundle of all 29 branches plus 13 uncommitted-diff patches saved to the sibling folder `AIUsageMonitor-worktree-backup-20261113/` (next to the repo) (bundle verified). Only `main` remains. |
| A2 | Confirm GPM's CPAMC priority changes | HANDOFF 2026-11-10/11-12 | Done (read-only). Every active account has a priority: Antigravity 20/10, Claude 40/30/20/10, Codex 20/10, xAI 10. |
| A3 | Unit test for `cpamc.load_base` (env > `.cpamc.env` > default) | HANDOFF 2026-11-12 | Done: `ProxyAddressTests` in `service/tests/test_service.py`. Compiles; not run (deferred). |
| A4 | `add-card.md` small-model gap test (was B5) | HANDOFF 2026-11-06 | Done. Haiku followed steps 1-4 in an isolated worktree; build ok (34% flash), not flashed. Gaps fixed in `add-card.md` (prerequisites line, ~20-line model card, full two-row sample, `build ok` is not the last line, missing-profile hint) and `customise-safely.md` step 3 (exit 0 check, art warnings expected, unchanged copy valid). Test worktree removed. |

## Dropped (stale notes, checked)
- HEALTH hook still probing `127.0.0.1:8317`: already fixed. `~/.agents/model-router/scripts/doctor.py` probes the Tailscale address (Home Repo catchup 2026-11-12).
- O6 P-Gemini default model: the 2026-11-10 handoff verified P-Gemini working on `gemini-3.8-flash-high`; that config lives outside this repo.

## owner
| # | Item | Needed |
|---|---|---|
| O1 | T-033.2 header `PROXY (n)` counts accounts; the ticket says it "should probably" count groups | decide: accounts or groups |
| O2 | T-033.4 next provider (Mistral Vibe etc.) | pick the provider; endpoint discovery needs their account |
| O3 | Run the README setup prompt on a clean checkout | it reflashes the device |
| O4 | Confirm Claude account 2 really reads 7d 0% in `/usage` | owner's account |
| O5 | Flash 7d at 0.41% rounds to 0% and counts as a cooldown | choose: keep, or tighten to true 0.00% |
| O7 | Review README tone and claims | owner review |
| O8 | Patch release for the CPAMC_URL change (service-only; `FW_VERSION` stays 1.16.0) | release decision |
| O9 | Retire the dead Console T3-cache sources, or source Console Antigrav/Argon from CPAMC | design decision |
| O11 | Apply CPAMC 429 cooldowns to the Flash (and Claude) pools too, like Argon | decide which window a cooldown zeroes: a Flash 5h cooldown would also zero 7d under the current per-pool rule |
| O12 | Delete remote branch `origin/t3/optional-pages-screensaver` (superseded) and the backup folders `AIUsageMonitor-art-backup-20261025/` and `AIUsageMonitor-worktree-backup-20261113/` | outward-facing (public repo) or irreversible: owner's call |

## blocked
| # | Item | Blocker |
|---|---|---|
| B1 | Updates tab update-available and conflict panels untested | needs a v1.17.1+ upstream release (see O8) |
| B2 | Resize recipe on a non-320x240 board | needs that hardware |
| B4 | Console Antigrav/Argon cards 5h-only | T3's stored login is a different Google account; waits on O9 |
| B6 | Backlog tickets T-018 audio visualizer, T-019 stock ticker, T-026 weather, T-008/T-009 MINT | feature work the owner has not scheduled |

## Assumptions
- No frontload questions: every auto item was specified by the repo notes.
- Testing rule: no suites run; `ProxyAddressTests`, `ProxyCooldownTests` and `ProxyResetCreditTests` are written and unrun.
- Owner rule "deleting merged worktrees is never an ask" covers the worktree cleanup; the one unmerged branch is preserved on `origin` and in the bundle.
- The add-card test stops at the build: flashing would replace the owner's running firmware with a test card.
