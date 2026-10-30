# Provider profiles

One JSON file per CPAMC provider (`<provider>.json`), worked out once. The collector loads every profile, calls `request` through CPAMC `/v0/management/api-call` for each active account, reads `windows` from the response, pools by `pool`, and sends the result. The firmware draws a tile from `tile`. A provider without a profile still gets a tile with an unknown ring and attention flags.

Fields:
- `hidden`: `true` keeps the group off the display (xai is hidden for now, making room for another provider).
- `request`: `method`, `url`, `header` (`$TOKEN$` is substituted by CPAMC), optional `data` (`{project_id}` is filled from auth-files), `fallback_urls`.
- `windows[]`: `pool` (ring group; one pool = one ring pair), `label` (auto from `length_s` if omitted), `path` (to the bucket in the body; `*` matches by `match`), `used` or `remaining` (field path) with `scale` (1 for a fraction, 100 for percent), `reset` (epoch or ISO path), `length_s` (path or constant).
- `tile`: `layout` (`rings` | `multi`), `pools` order and short labels.
- `fallback`: `headers` uses the observed auth-files signals when the live call fails.
- `notes`: discovery evidence (date, what's missing).

Discovered so far (2026-10-30): see docs/CPAMC_HOME.md "Live usage per group". claude, codex and antigravity are complete. xai has the reset only.
