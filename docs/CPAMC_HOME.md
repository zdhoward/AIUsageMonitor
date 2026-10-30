# CPAMC Home view — idea (2026-10-30)

Status: idea agreed; research next, then design, then implementation.

## Goal
A glance at what's left in the tank, per CPAMC proxy group. It replaces the
Console as the default Home. The Console stays selectable and configurable.

## Decisions
- **Unit of display:** one tile per CPAMC proxy group (e.g. "Claude — 16%"),
  laid out like today's Console tiles.
- **Quota windows:** match the current page (session/5h plus weekly) if CPAMC
  exposes them; research decides.
- **Group total:** pooled remaining. 2 accounts at 20% and 30% →
  (20+30)/200 = 25%.
- **Reset countdown:** only the next reset coming up in the group.
- **Danger icon:** only for things the owner must act on (expired or invalid
  auth, disabled account, proxy unreachable, config errors). Exhausted quota
  doesn't count, because waiting resolves it.
- **Data source:** CPAMC management API at `http://127.0.0.1:8317/`, using an
  API key kept out of the repo (env var / gitignored dotfile).

## Open questions for research
- Which endpoints expose per-account quota, windows and reset times?
- How are proxy groups defined and enumerated?
- Which account/auth states count as "needs attention"?
- Polling cost and rate limits; what to show when CPAMC is stale.
