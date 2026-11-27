# Provider profiles

One JSON file per CPAMC provider (`<provider>.json`), worked out once. The collector loads every profile, calls `request` through CPAMC `/v0/management/api-call` for each active account, reads `windows` from the response, pools by `pool`, and sends the result. The firmware draws a tile from `tile`. A provider without a profile still gets a tile with an unknown ring and attention flags.

Fields:
- `hidden`: `true` keeps the group off the display (xai is hidden for now, making room for another provider).
- `direct`: `"t3"` reads this provider with T3's own stored login (one account, `providers/<driver>/<profile>/antigravity-acp/acp_token.json`) and calls `request` directly, never through CPAMC. Its CPAMC auth files are ignored. Antigravity uses this since 2026-11-27 (Google suspended a proxied account).
- `request`: `method`, `url`, `header` (`$TOKEN$` is substituted by CPAMC, or by the service for `direct`), optional `data` (`{project_id}` is filled from auth-files or the T3 login), `fallback_urls`.
- `windows[]`: `pool` (ring group; one pool = one ring pair), `label` (auto from `length_s` if omitted), `path` (to the bucket in the body; `*` matches by `match`), `used` or `remaining` (field path) with `scale` (1 for a fraction, 100 for percent), optional `missing` (value to use when the field is absent, e.g. 0 for Antigravity, which drops `remainingFraction` once a bucket is spent), `reset` (epoch or ISO path), `length_s` (path or constant).
- `tile`: `layout` (`rings` | `multi`), `pools` order and short labels.
- `fallback`: `headers` uses the observed auth-files signals when the live call fails.
- `notes`: discovery evidence (date, what's missing).

Discovered so far (2026-10-30): see docs/CPAMC_HOME.md "Live usage per group". claude, codex and antigravity are complete. xai has the reset only.
