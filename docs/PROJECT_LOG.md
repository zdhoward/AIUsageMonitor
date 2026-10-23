# Project log

## 2026-10-23: visual-pages session handoff

- Reconciled stale handoff, ticket index, README and setup instructions with implemented T-008A. T-008 is partially implemented; B–L remain follow-up work.
- Recorded five-page COM6 flash/captures, source review, invalid independent visual review, portrait footer limitation and outstanding physical touch check. Tests deferred; no push/tag.

## 2026-10-23: default visual-page slice installed

- After owner-authorized free-model corrections, source review passed and main production build succeeded. Integrated five default-on entries and build-time validation, preserving a concurrent local footer-spacing fix.
- Flashed COM6 with hash verification; captured all five pages plus portrait Console and serial navigation wrap. Service resumed ACKs; restored landscape Console. Captures live under `docs/img/T-008A-*`.
- T-008A is a development slice, not full T-008 completion: automatic saver/MINT/scenes/assets remain pending. Physical tap acceptance is outstanding; portrait footer source age truncation is documented. Tests deferred; no push or release tag.

## 2026-10-23: first visual-pages implementation attempt

- Scoped T-008A and delegated to free routes. DeepSeek quota was exhausted; LiteLLM free-coder returned a patch with passing production build and scope checks.
- Independent free-review rejected header formatting and navigation/preview layout defects. Preserved patch in worker checkout `t3-c3af3620`; did not integrate or flash. T-008A records exact blockers and next corrections. Remaining implementation waits at the bounded routing limit.

## 2026-10-23: visual-pages plan review

- Reviewed T-008 against local main `60c67f2`, T-001/prototype `ed6355a`, firmware/service code and protocol/configuration/research docs. Main still has two views; installed prototype provenance is unconfirmed because flash records differ.
- Split delivery into dependent tickets with measurement gates, a navigable Screensaver preview independent of automatic activation, and PC-owned MINT through the existing serial service.
- Kept all available pages default-on and activation off; deferred extra asset importers/heavier rendering until tiny on-device probes justify them. Planning only: no implementation, tests, flash or push.

## 2026-10-23: visual pages implementation plan

- Consolidated optional navigation/screensaver requirements, PC-driven MINT, procedural scene ideas, and the future image/animation workflow into T-008 for Sol 6.1 review.
- Confirmed the existing newline-delimited JSON serial path is owned by the PC service; the separate bare CPU/RAM bridge sample would conflict and is excluded from the plan.
- Kept implementation details open and split delivery into reviewable slices; no firmware implementation was started.

## 2026-10-23: procedural screensaver scene research

- Added the MINT digital-pet concept: layered behavior, animation, rendering, and optional PC telemetry; noted serial-protocol and malformed-bridge questions before implementation.
- Recorded starfield, synthwave tiny-world, and ambient liquid concepts as optional procedural renderers, separate from the image conversion pipeline.
- Distinguished the liquid sketch's spring-surface impacts from the requested gradual fill and threshold-triggered self-drain cycle; outlined a simple staged prototype.
- Checked full-screen RGB565 buffer sizes and estimated the 40 MHz SPI transfer floor; 30 FPS remains unverified and requires on-device measurement.
- Added a small candidate implementation and validation plan without changing firmware or selecting unresolved design details.

## 2026-10-23: image and animation workflow research

- Recorded a source-backed recommendation to author separate named frames plus metadata and convert them offline to a compact ESP32 format; sprite sheets remain an import/packing option when mapped by metadata.
- Captured the board's framebuffer, flash-partition, and no-PSRAM constraints, and documented the current research boundary: procedural companion and placeholder only, no asset pipeline decision.
- Verified Aseprite export capabilities and LVGL GIF memory/filesystem requirements against primary documentation. The free routing shadow timed out; the research worker produced no draft, so the coordinator checked the sources directly.

## 2026-10-22: public documentation preview

- Owner selected MIT and local preparation only. Added license, safe example config and pinned pyserial dependency. GitHub stays private; no push, visibility change or release.
- Reworked README around the actual v1.4.2 framebuffer; added fresh-machine setup, implemented GPIO/power/bus details, serial/API reference and contribution guide. Removed current hardware identifiers/personal paths; preserved history and documented older MAC/path entries for owner review.
- Clarified that deadline refresh rereads local data, optional OpenRouter access reads an existing key, and framebuffer evidence does not verify physical viewing comfort. Updated handoff, test baseline and ticket/goal status. Firmware remains v1.4.2; no new firmware release is implied.
- Validation: 44 local documentation targets resolve, example settings load with localhost/115200 baud/OpenRouter disabled, CLI help confirms install syntax, installed library versions match the guide. Reused unchanged firmware build/flash/capture and 22-test baseline. No clean-machine install or new board verification claimed.
- Routing: hosted DeepSeek hit free quota; local Qwen produced no edits before cancellation. Coordinator completed documentation. Shadow run `94914ea8-9729-4c44-86c9-6899ccf6d2bb` recorded timeouts from both advisory backends; no independent model review claimed.
- Final integrated Gitleaks scan: 26 `main` commits through `3700cd0`, no leaks, exit 0. GitHub is still private with unchanged last-push time; local work remains unpushed. Advisory routing review has insufficient evaluation evidence for promotion; routing labels remain pending rather than treating fallback completion as proof of the cheapest lane.

## 2026-10-22: public GitHub release and session wrap-up

- At the user's direction, pushed documentation commits through `a7f2dd7`, changed `zdhoward/AIUsageMonitor` from private to public, and set the project description/topics. Verified remote visibility and branch synchronization; no open PRs.
- History contains an old board MAC address and local Windows paths. This was disclosed in the release checklist before the user requested public visibility. History was preserved; Gitleaks found no leaks across 26 mainline commits through `3700cd0`, and the final `a7f2dd7` release record was separately scanned staged. Current public docs omit those historical identifiers.
- Updated handoff, goals, ticket index and release record to reflect the completed public state. Firmware remains v1.4.2; no docs-only tag or new firmware release.
- Wrap-up check: previously green firmware build/flash/framebuffer and 22 service tests remain the applicable implementation baseline. Documentation checks found 44 valid local links and loaded the example config; final current docs-only edits do not warrant another firmware/test run. GitHub is public and no mergeable PRs are open.
- Retro: deterministic publication, doc and status checks used scripts/CLI (right); free DeepSeek exhausted quota and local Qwen timeout required coordinator completion (right fallback after observed failures). No independent doc review. No new shared rule or tool proposed; routing notes remain recorded in model-router. Advisory shadow evaluation remains insufficient for promotion.

## 2026-10-22: v1.4.2 reset readability

- Move console rings up 6px and use bright font 2 reset captions instead of muted font 1, for reading beneath a monitor.
- Wake the collector at upcoming reset deadlines; continue normal polling if the cached deadline remains due. This rereads T3's cache and transcripts, not provider endpoints; provider refresh still belongs to T3.
- Validation: 22 service tests pass; firmware built and flashed to COM6. Inspected `docs/img/v1.4.2-rings.png`: all six larger captions fit within their cards. Service restarted with deadline scheduling.

## 2026-10-22: session wrap-up

- User accepted v1.4.1. Reconciled handoff, ticket status and current docs; recorded final UI decisions in GOALS.md and removed superseded guidance from current-facing docs.
- Service healthy; 22 service tests pass; reused the green firmware build and final framebuffer. No open PRs to merge. Local commits/tags remain unpushed; retained partial worker checkouts.
- Retro: early paid implementation missed the routing preference; later delegation worked until quota/transport failures. Repeated intention-only worker results require a behavior/diff check, and unavailable routes should be suppressed instead of retried. See shared retro log for placement audit and applied routing improvement.

## 2026-10-22: v1.4.1 shared ring headings

- Grouped client count with the title; Session/Weekly column headings align with ring centers. Ring captions now show only reset countdowns, due, or unavailable. Cleared the data area below provider titles for future use.
- Delegated free-coder again returned only an intention and a version edit. Parent completed this small renderer adjustment locally; build and framebuffer inspection, no extra tests. Do not rely on this lane's terminal status as evidence of completion.

## 2026-10-22: v1.4.0 quota rings

- Replaced console bars and duplicate large values with Session/Weekly rings, exact remaining percentages centered, and muted S/W reset-table rows under provider names. Weekly stays yellow; session follows capacity thresholds. Landscape default and two-view navigation remain.
- Free-coder left a partial patch; the local Qwen continuation timed out before responding. Parent completed the two bounded renderer fixes (12-o'clock arc origin and portrait table spacing) and docs locally rather than restarting implementation. Runtime framebuffer inspection verifies the final layout.
- Local GPT-OSS review also produced no response/tool activity and was cancelled after three minutes. Parent reviewed the renderer and flashed frame directly. Empty-ring track contrast was raised after RGB332 inspection; no independent review pass is claimed.

## 2026-10-22: v1.3.4 weekly bar color

- Weekly bar fills are always yellow so they are distinct at a glance. Session bars and numeric warning colors retain their existing thresholds. Small renderer-only change performed inline; build/flash and framebuffer check, no extra tests.

## 2026-10-22: v1.3.3 separate quota bars

- Session (5h) is now always first, with weekly (7d) in its own bar underneath. Each has an independent percentage, color, and explicitly labeled reset countdown; missing windows stay unknown. Kept landscape default and exactly two views.
- OpenCode DeepSeek implemented; local Ollama GPT-OSS reviewed after Beam's free quota was exhausted and the configured LiteLLM review model was absent. Build and scoped verification passed; parent checks the flashed framebuffer. No test suite expansion.

## 2026-10-22: v1.3.2 landscape redraw

- Framebuffer inspection after flashing landscape caught startup pixels at the right edge. Clear the explicit rotated canvas dimensions rather than the TFT base class's screen extent.

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
