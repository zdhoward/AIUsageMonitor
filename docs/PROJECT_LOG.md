# Project log

## 2026-10-24: daylight brightness installed

- Owner authorized paid Codex low effort after bounded free attempts failed. Corrected API vocabulary/UTC handling, startup failure, cache/ramp logic, runtime configuration and firmware interpolation; added Windows timezone dependency and setup guide.
- Production build passed at 420,143 bytes flash / 29,808 bytes static RAM. Runtime import, live API and temporary HTTP startup/shutdown passed; final source inspection completed. Original independent free review identified rejected-patch blockers; final review was coordinator inspection.
- Flashed COM6 with hash verification and restarted main service. Live health reports the owner's city night duty 40, 1000ms smoothing, nine cached dates, no brightness errors and resumed serial ACKs. Evidence in `build/t011-*`; physical calibration and broader acceptance pending. Automated tests deferred; no release/tag or push.

## 2026-10-24: daylight brightness implementation blocked

- Specified PC-owned SunriseSunset.io scheduling for the owner's city with configurable levels, centred fades, caching and ESP PWM updates in T-011.
- First free route exhausted quota; fallback returned a patch and claimed build/syntax success. Runtime import fails on a missing function; source inspection found incompatible API status values and incomplete configuration/transition behavior. Preserved worker patch without integrating or flashing it.
- Two implementation attempts consumed; correction waits for fresh owner authorization under model-router. Independent review fallback pending. Automated tests deferred to owner testing phase; routing cost UNKNOWN.

## 2026-10-23: per-view idle screensaver

- Owner authorized paid low-effort implementation after both free workers hit usage limits. Enabled 30-second idle saving for Console/Details with separate enable, timeout and usage-wake settings; Face/Images remain exempt.
- Screensaver is automatic presentation state, removed from navigation and pagination. Tap wakes the original view. Explicit measurement comparison ignores heartbeat, clocks, countdowns, source age and MINT updates; changes restart the idle interval.
- Production build passed at 419,663 bytes flash / 29,760 bytes static RAM; COM6 flash hash verified. Automated tests deferred to owner sprint end; acceptance cases retained in SCREENSAVER.md. Free independent review unavailable; coordinator source inspection completed. Device framebuffer evidence recorded in T-010.
- Wrap-up reconciled current behavior and open acceptance in GOALS.md, T-008, HANDOFF.md and TEST_REPORT.md. Local `main` remains 31 commits ahead of origin; no open PRs or new tag. Untracked `assets/` preserved.

## 2026-10-23: Grobot MINT implementation

- Owner selected a simple Grobot-based full-screen face and authorized paid Codex low-effort slices after two free routes returned no patch. Integrated seven blending emotions, independent blink/gaze/mouth/sweat and pinned MIT adaptation.
- Added PC-owned gradual mood, finite pet/play/nap API, optional default-off Windows CPU/RAM hysteresis, and additive expiring serial state through the existing port owner. Review caught restart ordering after clock rollback and full-uptime-wrap lease resurrection; both corrected and independently reviewed.
- Worker production builds and Python syntax checks passed; final worker firmware is 418,659 bytes flash and 29,000 bytes static RAM. Tests remain deferred to owner sprint end. Hardware evidence is being collected separately; no release or performance claim follows from build success.
- Device capture exposed missing mouth. Rectangle rendering alone did not fix it; corrected unsigned delta negation before exponential blending. Final build: 418,663 bytes flash / 29,000 bytes static RAM; COM6 flash hash verified and current service resumed ACKs. Happy/idle framebuffers now show eyes and mouth. Sustained motion and broader acceptance remain pending; no tag/push.

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

## 2026-10-24 — Image/GIF playback and synthwave city scene

- **Offline conversion, not on-device decoding:** `scripts/asset_convert.py` turns GIF/PNG/Aseprite into RLE RGB332 C++ data; the ESP32 only blits. Keeps heap flat (238 KB free) and assets small (~21 KB total).
- **Aseprite is the art format** for scenes (layers + tags); the generated `assets_gen.*` are committed so builds don't need Aseprite.
- **Hybrid city scene:** static art from Aseprite, life in code (rain, sun, grid, blinks, lightning, traffic). Measured 54 ms/frame (~18 fps) on the board. See [ASSETS](ASSETS.md).

## 2026-10-25 — v1.5.0: Scene Studio, scene engine and live tuning

- **Studio as a local web app** (`python -m studio`, `Scene Studio.cmd`) rather than PySide6: easier to make look good, no new dependencies.
- **One engine, two hosts:** the firmware scene engine is built into a Windows DLL for the Studio's previews. Previews match the device, and effects are written only in C++.
- **Tune blobs** (`tune.h`) carry unsaved edits to both the preview and the device (`!TUNE`), so tuning needs no reflash.
- **Profiles own layout:** pages, `scene:<id>` pages, up to 16 playlists, screensaver target and ring colours are compiled from `profiles/*.json` into git-ignored headers.
- **Licensing:** third-party packs stay git-ignored (the repo is public). Only CC0 art is committed (Ansimuz Miami-synth and cyberpunk-street, PixelPatterns). The GPL open_spectre and the unlicensed Video_eq were used for ideas only; termflix and sysc-Go (MIT) ideas are credited per entry.

## 2026-10-25 — v1.6.0 System page and serial-thread fix

- **Fix:** the display stopped updating because a Studio pause cleared the serial handle mid-write and the uncaught `AttributeError` killed the serial thread silently (pythonw has no stderr). The loop now uses a local handle and survives any exception.
- **System page** (`system`): CPU history and per-core bars, memory, disk and network rates, top three processes. Stats travel as a separate 1 Hz `{"t":"sys"}` line so the 4 KB usage push keeps its cadence; the device keeps 60 s of history. Needs `psutil`. No GPU stats (no vendor-neutral source without extra tooling).
- **System page redesign** (same day): owner wanted CPU, RAM, GPU, disk R/W, upload and download only, no graphs, smoother updates. Dropped histories and the process scan (it blocked the serial loop every 3 s, causing stutter). Added GPU load from Windows "GPU Engine" PDH counters via ctypes (busiest engine type, as Task Manager shows). Values ease on the device at ~250 ms.

## 2026-10-25 — v1.7.0 Theme shift replaces per-theme copies

- **Two entries per scene:** the original (its picked theme) and `<id>-shift`, which cross-fades through the ticked themes. All themes are ticked by default (a scene with no `cycle` uses every theme). `variants` is retired. The owner wanted fewer near-duplicate copies and themes they can edit in one place.
- **Studio:** the theme list ticks themes for the shift, a toggle previews the original or the shift, and hold and fade are always editable. Tune blobs carry the cycle only for the shift entry. `MAX_CYCLE` went from 5 to 16 (needs a reflash for live tuning on the device).
- **Fix:** on Windows, `SO_REUSEADDR` let a second Studio bind port 8798 alongside the first, so requests split between old and new code (broken previews, settings that "did nothing"). The server now binds exclusively, so a second launch only opens a window.
