# Usage data sources

Baseline verified 2026-10-21 against T3 Code server 0.1.1. Local source files and databases are read without modification. The service sends no prompts and does not refresh logins. Cache, database and transcript schemas are implementation details of their respective applications and may change.

The default transport is USB serial. No subscription OAuth credentials are needed by the firmware or collector. The optional OpenRouter status source is different: when enabled (the code default), it reads `OPENROUTER_API_KEY` or falls back to OpenCode's local `auth.json`, and sends that key only to OpenRouter's HTTPS status endpoint. The supplied example config disables this source; enable it deliberately if wanted. Keys are never part of the device payload.

| Source | Where | Metrics | Freshness |
| --- | --- | --- | --- |
| **T3 provider status cache** | `~/.t3/caches/<instance>.json` → `usageLimits`, `auth.label`, `displayName`, `accentColor` | Session (5 h) and weekly windows: used %, reset time, check time. Covers each Claude account (CL1 = `~/.claude`, CL2 = `~/.claude2`) Codex and Gemini (`antigravity` driver, 5 h and weekly windows). | T3 rewrites it every ~5 min while running. The service shows the age and flags it stale after 20 min. |
| **Codex session logs** | `~/.codex/sessions/**/rollout-*.jsonl`, `event_msg/token_count` | Per-step tokens (input, cached, output, reasoning) and model (`turn_context`). Each event also carries `rate_limits`, the same windows T3 shows. | Written after each model step, so effectively live. The newer of this and the T3 cache wins. |
| **Claude Code transcripts** | `<CLAUDE_CONFIG_DIR>/projects/**/*.jsonl`, `assistant` lines | Per-message tokens: uncached input, cache read, cache write, output. Model. Deduplicated by message id + request id. | Written as each message completes. There is no per-token streaming data. |
| **T3 orchestration state** | `~/.t3/userdata/statev2.sqlite` (read-only): `orchestration_v2_projection_runs`, `..._provider_sessions` | Which provider instance has a run in progress, its model, and the number of running runs. | Live: T3 updates the row when a turn starts and ends. |
| **T3 price table** | `~/.t3/userdata/usage-model-rates.json` (the LiteLLM price list T3 downloads) | USD per token, so the service can estimate **API-equivalent** cost. | As refreshed by T3. Models without a price are counted as "unpriced". |
| **OpenCode database** | `~/.local/share/opencode/opencode.db` (read-only): `session_message` (v2) + legacy `message` | Free and other-provider activity: provider, model, tokens, and provider-reported cost (OpenCode Zen free models, NVIDIA, OpenRouter, local LiteLLM chains). | Written per message. |
| **OpenRouter key status** | `GET https://openrouter.ai/api/v1/key` using `OPENROUTER_API_KEY`, or OpenCode's local `auth.json` as a fallback | Free-model daily requests (used/limit/remaining), actual spend (daily/monthly), budget remaining, free-tier flag, when present in the response. | Polled every 10 min when enabled. This is a status call; it sends no prompt. |

## Unavailable or limited

- **NVIDIA NIM:** there is no public usage, credit, or rate-limit API for `integrate.api.nvidia.com` keys. Only request counts seen in OpenCode history can be shown.
- **LiteLLM:** no direct proxy integration is implemented. Traffic recorded under OpenCode's `litellm` provider entries can be attributed from that history; the upstream model that answered after proxy fallbacks is not necessarily visible.
- **Claude live streaming:** transcripts record usage per completed message, not per token. "Running" status comes from T3, not from token flow.
- **Subscription spend:** Claude Pro and ChatGPT Plus report only quota percentages. The cost shown is an API-equivalent **estimate**, never a bill.
- **T3 RPC/HTTP API:** it requires a paired session token. Pairing would change T3's auth state, so it was not used. The cache files hold the same limits T3's UI shows.
- **Direct Anthropic `api/oauth/usage` probing:** T3 already does this. Repeating it would mean reading OAuth tokens in this service, so it was skipped.

## Reset deadlines and freshness

The collector normally rereads local sources every 10 seconds and also wakes at the next known reset deadline. Passed deadlines continue normal polling rather than creating a busy loop. New payloads reach USB every 5 seconds by default. A cache read is not a provider query: `due` may remain visible until T3 or a transcript contains a newer measurement. Percentages are retained rather than assuming a refill.

The display's source age is based on the provider check time, not serial delivery time. An active USB connection can therefore coexist with stale provider data. Staleness defaults to 20 minutes; the firmware also marks a disconnected link stale after 30 seconds.
