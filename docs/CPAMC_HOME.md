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

## Research findings (2026-10-30, live CPAMC)
Source: `GET /v0/management/auth-files` with `Authorization: Bearer <management key>`.
One call returns every account, so it's the only endpoint Home needs.

Per account: `provider` (the proxy group: claude, codex, antigravity, xai, devin),
`status`, `status_message`, `disabled`, `unavailable`, `cooldowns[]`,
`quota.observed_at`, `quota.signals`, `success`/`failed`, `recent_requests[]`
(10-minute buckets), `last_refresh`.

Quota signals are upstream rate-limit headers that CPAMC captured on the
account's last request:
- **claude:** `Anthropic-Ratelimit-Unified-5h-Utilization`/`-Reset` and
  `-7d-Utilization`/`-Reset` (0–1 utilization, epoch reset), plus `-Status`
  (`allowed`, `allowed_warning`, …). These give the same session and weekly
  rings as today.
- **codex:** `X-Codex-Primary-Used-Percent`/`-Reset-At`/`-Window-Minutes` and
  `Secondary-*`. Window lengths vary by plan: Plus has a short primary window;
  Free shows a 43200-minute (30-day) primary with an empty secondary. Rings
  must be labelled from `Window-Minutes`, not assumed.
- **antigravity, xai, devin:** no quota signals. The only limit information is
  `cooldowns[]` (`reason: quota`, `retry_at`, per model).

Caveats:
- Readings are observed, not polled, so they're only as fresh as the account's
  last proxied request (`observed_at`). Past resets should be shown as stale or
  refilled rather than trusted.
- `/v0/management/usage` returned an empty body; Home doesn't need it.
- Needs-attention candidates: `status` not `active`, `unavailable`, a
  non-empty `status_message`, auth refresh failures, proxy unreachable.
  `disabled` may be intentional (devin is currently disabled).
