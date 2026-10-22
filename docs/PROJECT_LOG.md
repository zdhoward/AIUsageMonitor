# Project log

## 2026-10-22: v1.3.1 landscape default

- Corrected the default to rotation 1 (320×240 landscape). The final UI instructions superseded the earlier portrait request; firmware and current UI docs now agree. This is a small configuration fix performed inline, followed by build/flash and a framebuffer capture.

## 2026-10-22: v1.3.0 final two-view console

- User clarified exactly two views: original details and one status console. Removed the extra generated account pages; the two-entry render registry remains easy to extend later.
- Applied the supplied instrument-panel design: dark palette, fixed Claude A / Claude B / Codex rows, urgent measured quota prominent, separate secondary quota, resets, source age and visible stale status. Rotation 0 stays the portrait default; layout adapts to orientation. Brightness and warning thresholds are configurable.
- Free OpenCode DeepSeek implemented the final UI and cache fixes; free Beam reviewed it. Existing 22 service tests and ESP32 build pass; no expanded test suite. Parent integrates and flashes, with framebuffer screenshots as render evidence.
- Cached sections survive missing data; valid zeros replace old values, including reset credits. Retained-window countdowns age correctly and cached OpenRouter numbers remain visible during source errors.

## 2026-10-22: v1.2.0 display refresh

- Retain measured quota percentages through stale/missing readings and passed reset deadlines; keep readings bright during connection loss. Reset deadlines do not imply a refill. Cache is in device RAM, not flash.
- Default to rotation 0, traditional landscape left edge up, for the clockwise portrait remount.
- Add a glanceable overview, generated account focus pages, and the detailed dashboard. Whole-screen CST820 tap/release cycles views. Bars ease toward new readings; numeric percentages stay exact.
- Keep UI tuning in `ui.cpp` and document extension points in `docs/UI.md` / `docs/UI_HANDOFF.md` for a later Claude pass. No additional provider calls or libraries.
- User prefers practical runtime validation over an expanded suite. Existing 22 service tests pass; firmware build and framebuffer checks are used. Physical touch, orientation, and viewing distance remain user acceptance checks.

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
