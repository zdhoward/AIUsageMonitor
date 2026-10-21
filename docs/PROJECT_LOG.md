# Project log

## 2026-10-21: v1.1.0

- **Show quota left by default** (`SHOW_REMAINING 1`, user preference), keeping "used" as a config option. Colours stay keyed to usage so red always means "nearly out", whichever number is shown.
- **Reset credits** come from T3's cache (`usageLimits.resetCredits.availableCount`, the same count T3 shows next to **Use reset**). They are sent only when above 0 and shown as `Pro (Nx reset)`.
- Done inline rather than delegated: three small edits, and the firmware half needed the device loop.

## 2026-10-21: v1.0.0

- **Hardware identified before any code.**
  - Every sketch in `Documents/Arduino` targets an ESP32-2432S024 (ILI9341 + CST820) with the same TFT_eSPI pins.
  - esptool confirmed an ESP32-D0WD-V3 behind a CH340 on COM6.
  - The old flash (TickrTrackr/tests) was overwritten without a backup, at your direction.
- **Quota data comes from T3's provider caches** (`~/.t3/caches/*.json` → `usageLimits`), not T3's API. The RPC needs a paired session, which would change T3 auth state. The caches hold exactly what Usage → Limits shows, and T3 refreshes them about every 5 min.
- **No direct calls to Anthropic or OpenAI usage endpoints.** That would need reading OAuth tokens. Codex logs already carry `rate_limits` per token event, so Codex limits are near-live without any token.
- **Tokens and cost come from local transcripts** (Claude JSONL, Codex rollouts), read incrementally, and are priced with T3's own rate table. The display labels them as estimates.
- **Free models: OpenCode DB.** The LiteLLM proxy has no spend database and its logs have no timestamps, so OpenCode's history is the record. OpenRouter's `/api/v1/key` adds the free-request allowance (x/50/day) at no quota cost.
- **USB serial instead of Wi-Fi.** The PC is on Ethernet with a Public firewall profile, and Wi-Fi would need credentials in firmware plus a firewall rule. The device is always on USB, so the service stays on localhost. Wi-Fi remains an opt-in compile flag.
- **Port 8797:** 8787 was already used by another local Python service.
- **Rotation 2 default:** derived from TFT_eSPI's ILI9341 MADCTL table relative to your landscape `setRotation(1)` (see HARDWARE.md).
- **Screenshots from the frame buffer** (`!SHOT`) are used as on-device render evidence, rather than turning on the webcam without asking.
- **TFT pins as build flags** (`USER_SETUP_LOADED`), so the shared library's `User_Setup.h` stays untouched.
- **Autostart** is a per-user logon scheduled task, mirroring how model-router starts LiteLLM.
