# Catchup ledger (2026-11-07)

Sources: HANDOFF.md, tasks/lessons.md, .tickets/*, `gh issue list` (none open), TODO/FIXME grep (none). Tree clean at `bbbb320`.

## auto
| # | Item | Source | Note |
|---|---|---|---|
| A1 | T-033.1 Antigrav multi tile bottom `7d` line clipped | T-033 | firmware; needs build, flash COM6 and framebuffer capture as done criteria |
| A2 | T-033.3 Single-window pool (Argon) draws only inner ring | T-033 | firmware; same done criteria; bundle with A1 |
| A3 | Unit test for `tz` and for `rc` in `pool_groups` | HANDOFF | write only; running is deferred to the testing phase |

## owner
| # | Item | Needed |
|---|---|---|
| O1 | T-033.2 header `PROXY (n)` counts accounts, handoff says it "should probably" count groups | decide: accounts or groups |
| O2 | T-033.4 next provider (Mistral Vibe etc.) | pick the provider; endpoint discovery needs their account |
| O3 | Run the README setup prompt on a clean checkout | reflashes the device; owner's call |
| O4 | Confirm Claude account 2 really reads 7d 0% in `/usage` | owner's account |
| O5 | Flash 7d at 0.41% rounds to 0% and counts as a cooldown | choose: keep or tighten to true 0.00% |
| O6 | P-Gemini default model in `~/.codex_cpamc` (`gemini-3.8-flash-high`) | outside the repo |
| O7 | Review README tone and claims | owner review |
| O8 | Reflash firmware or bump `FW_VERSION` (still 1.16.0) | release decision |
| O9 | Decide retiring the dead Console T3-cache sources | design decision |

## blocked
| # | Item | Blocker |
|---|---|---|
| B1 | Updates tab update-available and conflict panels untested | needs a v1.17.1+ upstream release |
| B2 | Resize recipe on a non-320x240 board | needs that hardware |
| B3 | Manual-reset expiry dates | no data source exists |
| B4 | Console Antigrav/Argon cards 5h-only | T3's stored login differs from the CPAMC accounts; needs a source decision (see O9) |
| B5 | `add-card.md` small-model gap test | model lanes exhausted (HEALTH FAIL, all pools) |
| B6 | Backlog tickets T-018 audio visualizer, T-019 stock ticker, T-026 weather, T-008/T-009 MINT | feature work not scheduled by the owner |

## Assumptions
- No frontload questions were asked: the open auto items are specified by T-033 and need no answers.
- The Testing rule applies: no suites run, and the unit tests in A3 stay unrun.

## Status
- A1 done: Antigrav multi tile rings shrink with tile height; the `7d` line is inside the panel (`build/t033-fix.png`).
- A2 done: a weekly-only pool (Argon) and single-window tiles draw only the inner ring (same capture).
- A3 done: `ProxyResetCreditTests` added for `rc`. A `tz` test already existed (the handoff was stale). Not run: deferred to the testing phase.
- First catchup pass stopped early because a stale pool-status HEALTH FAIL was read as a hard block; the work was done inline instead. No reviewer pass (slot unavailable); diff is small and checked against the capture.
