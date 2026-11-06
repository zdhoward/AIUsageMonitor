# Handoff — safe-update flow, agent guide, Studio Updates tab (2026-11-06) — CURRENT
- Done: `AGENTS.md` + `docs/recipes/*` + `scripts/doctor.ps1` for agent-guided customising and updates; users work on a `my-setup` branch with `profiles/my.json`, `main` mirrors upstream. Studio **Updates** tab backed by `studio/updater.py` (check, trial-merge preview, backup tag, abort on conflict with an agent prompt, flash/restart, undo). Fixed a stale-backup-tag bug and added the missing `tz` test. Docs updated (README, SETUP, STUDIO, CONTRIBUTING, TEST_REPORT, PROJECT_LOG). All pushed to `main`; version still 1.16.0, no release made.
- Validation: service 56 OK, Studio 29 OK, third-party check PASS (run this session). UI checked visually for the Updates tab only in its idle state.
- Open: (1) update-available and conflict panels untested through the UI against a real newer upstream. (2) Run the README setup prompt once on a clean checkout (reflashes). (3) Resize recipe unverified on any non-320x240 board. (4) Have a small model follow `add-card.md` to find gaps. (5) Studio must be restarted to load new code after an update. (6) Decide whether to cut a release (v1.17.0) for the new flow; owner's call.

# Previous: v1.16.0 release and README rewrite (2026-11-06)
- Done: Messages card redesign (large rows, colour headings, even spacing, percent drops when the name would be cut). Proxy header shows local date/time from `ts` + new `tz` (service sends `time.localtime().tm_gmtoff`). Released **v1.16.0** (tag + GitHub release, firmware 1.16.0 flashed to COM6, service restarted). Docs updated: README, PROTOCOL (`tz`), UI, `RELEASE_1.16.0.md`, PROJECT_LOG; `docs/img/display-proxy.png` replaced. README then rewritten for discovery (pitch, AI-guided setup prompt with frontloaded questions, customisation prompts); commit `68d7372`. All pushed, no open PRs, tree clean.
- Decision: manual-reset **expiry dates are not available** (Codex `wham/usage` and T3's cache give counts only); the card shows counts. Owner may know another source (e.g. whatever T3's "Use reset" shows).
- Validation: firmware build 45% flash, hash-verified flash, framebuffer inspected (`build/messages-ui4.png`). No tests run (owner declared none needed); nothing covers `tz`.
- Open: (1) run the README's AI setup prompt once on a clean checkout (never executed end to end; it would reflash). (2) Owner review of README tone/claims. (3) Add a unit test for `tz`. (4) Earlier items below (console Antigrav source, Claude pool 7d check, Flash 0.41% rounding) still stand.

# Handoff addendum — Antigrav cooldown label and weekly source (2026-11-05)
- Finding: the Antigrav tile's amber "COOLDOWN" was the soonest 0% window across all pools and both accounts' average, here the Claude pool's `3p-weekly`, not the Gemini weekly (97.7 h, correctly outside the 24 h burn pile). Verified against live CPAMC buckets and the owner's agy `/usage` (Gemini weekly 97h, Argon 93h, 5h 44m all match).
- Done (firmware, flashed to COM6, pushed; commits `c87ed01`..`b5703b7`, last capture `build/cd-plain.png`): the multi tile's top-right is now **only Flash's soonest 7d cooldown, as a bare countdown** (judged per account via `q[]`/`qz[]`, 5h ignored, `proxyCooldown(..., onlyPool=0)`). The Gemini-side "Cl/GPT" pool is labelled **Claude** (no GPT models; profile `antigravity.json`). A weekly-only pool (Argon) shows its next reset in the empty 5h line under the ring. Single-account tiles (Claude/Codex) use the same per-account weekly rule; Claude's title turned amber because one of its four accounts reads 7d 0%, unconfirmed by the owner.
- Done (service): the direct Antigrav probe also calls `retrieveUserQuotaSummary` (agy `/usage` source) for `gemini-5h`, `gemini-weekly` and Argon's weekly, falling back to models-only. 54 service tests pass (3 new, run after that change; the later firmware-only commits ran no tests). Docs: `DATA_SOURCES.md`, `UI.md`.
- Open: (1) T3's stored Antigravity login is a different Google account from the two CPAMC ones and returns only `3p-*` buckets, so the **console** Antigrav/Argon cards stay 5h-only/unknown; option: source them from CPAMC. (2) Claude pool 7d reads 50% (average of two accounts); owner should check account 2 in `/usage` to confirm it is really 0%. (3) A Flash 7d at 0.41% rounds to 0% and counts as a cooldown; tighten to true 0.00% if the owner prefers. (4) Firmware version not bumped.

# Handoff addendum — Console Codex "unsupported" fix (2026-11-05)
- Done: console Codex tile showed "unsupported". Cause: T3 names the ChatGPT account by UUID (stale cache, "unsupported"), while `snapshot._merge_codex_log_limits` only matched an account with id `codex`. Now falls back to the ChatGPT-plan Codex account with no windows when no exact id exists. Commit `7fc7c6a`; service restarted; device payload shows 5h 12% / 7d 79% (source `codex_log`).
- Expected, not a bug: API-key proxy accounts (P-Codex, P-Gemini, P-Grok, P-Claude) stay "unsupported" on the console. The Proxy view reads CPAMC and was always correct.
- Limit: log-based reading is only as fresh as the last Codex use.
- Deferred: tests (owner testing phase); no test yet for the fallback match. Optional: friendlier label or hide for API-key accounts.

# Handoff addendum — Proxy Messages card (2026-11-03)
- Done: last Proxy grid cell (under System) is a MESSAGES card. **24HR BURN PILE** lists accounts with quota left in their full-reset window (pool's longest, 7d/30d) resetting within 24 h, soonest first. **MANUAL RESETS** lists accounts with banked resets (`Codex1 x2`). Commits `aa527cf`, `0ee0c16`, `0711c64`; flashed to COM6, service restarted, framebuffer `build/messages-card.png` inspected.
- Data: service reads `rate_limit_reset_credits.available_count` from Codex `wham/usage` (profile key `reset_credits`) and sends per-group `rc` array (sector order, -1 unknown) on the proxy line. Counts available, not `applicable_available_count` (owner OK).
- Limit: no expiry/earned date for banked resets exists in Codex `wham/usage` or T3's cache; owner accepted count-only. Claude reports no manual resets.
- Deferred: automated tests (owner testing phase); no test yet for `rc` in `pool_groups`. Firmware version not bumped.

# Handoff addendum — commit identity cleanup (2026-11-03)
- Cause: agent sessions on 2026-10-27/28 committed with invented emails (`zech@users.noreply...`, `197633046+agricidaniel@users.noreply...`), so GitHub credited users `zech` and `kglxeee` (ID 197633046). Only collaborator is zdhoward; no outside contributions.
- Fixed: `git filter-repo --mailmap` rewrite of remote branches and tags; force-pushed `main` (`ac27eb6`), v1.14.1, v1.15.0, v1.15.1. All main commits now use `3210164+zdhoward@users.noreply.github.com`. Global CLAUDE.md/AGENTS.md/GEMINI.md now forbid overriding commit identity; synced.
- Caution: local T3 worktree branches still hold pre-rewrite history; rebase onto new `main` before merging or pushing any of them.

# Current handoff — v1.16.0 (2026-11-06)
- v1.16.0 released: Proxy header clock (`ts` + new `tz`), redesigned Messages card. Firmware 1.16.0 flashed to COM6, service restarted. Open: manual-reset expiry dates have no known data source (counts only); no test covers `tz`. Tests deferred.

# Previous handoff — v1.15.1 patch (2026-11-03)
- v1.15.1 released (service-only): 5h forced to 0% left when 7d exhausted (tiles + proxy rings), Antigravity earliest-reset fix. 51 tests pass, service restarted, ESP32 acking. No open PRs. Next: owner visually confirms the Codex ring on the device; firmware still 1.15.0.

- Owner authorized public GitHub release and accepted the installed account-sector spacing. Release target is `v1.15.0` on `main`; release URL: https://github.com/zdhoward/AIUsageMonitor/releases/tag/v1.15.0. No open PRs at wrap-up.
- **Antigravity reset fix:** Antigravity session and weekly `resets_at` now use the earliest upcoming reset across Gemini models instead of the worst model's reset, so countdowns match real refills.
- **7d exhaustion rule:** an account whose 7d window has 0% left now shows 0% left on its 5h window, on account tiles (`snapshot.build_payload`) and proxy rings (`cpamc._exhaust_short_windows`, e.g. Codex). 51 tests pass; service restarted and the ESP32 acks pushes.
- Completed: preserve both Codex accounts' live quotas, anonymous stable account ordering, equal session/weekly sectors, 10-degree gaps, aggregate figures/earliest upcoming reset captions, unknown versus zero, and recovered-account warning correction. Successful current probes supersede stale proxy error metadata; failed probes retain quota without claiming current health. No inferred refill from an elapsed deadline.
- Implementation commits: `7a977c9`, `e15856f`, `3cea6ec`; release preparation follows. Main implementation used owner-requested Terra 6.1; coordinator reviewed core diff and made the small warning/gap changes. No independent review claimed for those adjustments.
- Verification: production builds, hash-verified USB uploads and live two-Codex-account probes passed. Inspected USB framebuffers `build/multi-account-live.png` and `build/sector-gap-live.png`; public evidence is `docs/img/display-proxy.png`. Versioned build/upload logs use `build/v1.15.0-*`. Automated tests remain deferred to owner testing phase; wrap-up does not authorize them.
- Release is source-only: existing third-party obligations for prebuilt binaries remain unresolved. Optional CC0 scene pack stays on v1.14.1. Do not publish local merged firmware, private settings or art. Public push guard installed; never bypass it.
- Next: owner testing phase should cover account removal, missing readings, current auth failure/recovery, more than eight accounts and serial fallback, portrait/Rows and retained tests. T-033 items 1–4 (clipping/layout/header/provider polish) remain open; version item is completed. T-026 weather and earlier backlog remain unchanged.
- Efficiency: deployment and framebuffer inspection belong in the implementation's done criteria; the first handback left the owner waiting for installation. Reuse existing build/flash/capture scripts and report deferred tests explicitly. Token/cost totals UNKNOWN; no routing promotion justified.

## Earlier handoff

# Handoff addendum — P-Gemini drained Codex (2026-10-30)

- Cause: T3 provider `codex_proxy_gemini` ("P-Gemini") points at CPAMC. Antigravity offers no Sol/Codex models, so a P-Gemini + `gpt-6.1-sol` favorite was served by the Codex Plus account (5h 100%, 7d 90% used; 5h resets 23:38 UTC). The Antigrav "Cl/GPT" tile was correct (pool untouched).
- Fixed (outside repo, `~/.t3/userdata/settings.json`, backup `.bak-20261030`): removed that favorite; P-Gemini now hides all built-in Codex models and lists only Antigravity models.
- Open: P-Gemini has no default model in `~/.codex_cpamc`; set `model = "gemini-3.8-flash-high"` at the source and sync. Optional: CPAMC block for Codex model names from P-Gemini. Optional: relabel tile "Cl/GPT" -> "Cl/OSS".

# Handoff — CPAMC Proxy home view (2026-10-30)

## Done
- The Proxy view is the default home (firmware merged in `2e7fb8c`, service `fdca048`, xAI text and hide `14083cf` and later). Flashed to COM6, service restarted, live data confirmed by framebuffer capture (Claude, Codex, Antigrav multi tile, System card). Console stays selectable.
- Data: `service/aimon/sources/cpamc.py` polls `/v0/management/auth-files` every 30s and live usage per account through `/v0/management/api-call` every 5 min, using `service/aimon/profiles/*.json`. Keys live in gitignored `service/.cpamc.env` (CPAMC_API_KEY, CPAMC_MANAGEMENT_KEY). Serial `proxy` line every 10s; contract in .tickets/T-028.md.
- Design, research and endpoint evidence: docs/CPAMC_HOME.md. Terms: GLOSSARY.md (Proxy group, Provider profile, Usage window).
- Rate-limit/quota states never raise the danger flag. xAI is hidden (`"hidden": true`) because it reports no limit.

## Validation
Live CPAMC polls and four device captures inspected by the coordinator. Firmware build ok. Service/firmware test suites NOT run (sprint-end policy); no tests were added for cpamc.py yet.

## Next
- T-033: Antigrav bottom-line clipping, header count, Argon ring, version bump and tag, next provider (e.g. Mistral Vibe profile).
- Add retained tests for `cpamc.pool_groups`/`read_windows` with redacted fixtures at sprint end.
- Old Console T3-cache sources are effectively dead under CPAMC; decide whether to retire them.
- Still open from before: T-026 weather plan and the items listed below.

# Handoff — public releases, licensing and weather roadmap (2026-10-28)

## Session closed

- Public releases: v1.14.0 Studio/settings hardening, then v1.14.1 licensing/docs/GIF and optional CC0 scene pack. Main synchronized through weather-plan commit `5255f0f` before this closing documentation commit; no open PRs to merge. Installed firmware remains v1.14.0.
- Validation already completed: 49 service +20 Studio tests, browser settings/scene checks, production build/hash-verified flash and framebuffer inspection. Later licensing tools: compilation, scoped inventory check, production GIF rendering and archive inspection; automated tests for these tools remain deferred. No validation rerun for this docs-only close.
- Next concrete action when work resumes: select/scope T-026's provider and shared-location migration, then implement cached weather data/page before ambient weather/daylight synchronization. It is not enabled. Other open items: independent Argon quota source; PixelPatterns license provenance; exact historical procedural derivation; full binary redistribution obligations; portrait/Rows/logon/physical brightness/Wi-Fi acceptance. Optional T-020/feature ideas stay on backlog.
- Retrospective: require an evidence table with actual upstream license text/revision before writing license conclusions or acquisition tools; do not invent authors or use generic CC0 text as pack evidence. Match UI units/ranges to runtime validators before delegation. Reuse saved scripts and bounded output; paid coordination/rework cost UNKNOWN, no model promotion/savings claim. These project instructions are applied; effectiveness awaits later work.

## Next feature plan: T-026

Weather page plus optional local weather/daylight parallax synchronization is recorded in .tickets/T-026.md. Planning only. Reuse private location and solar cache, separate daylight from backlight, preserve authored/random/manual modes, and isolate network work from quota refresh/serial. Provider/deployment rights, shared-location migration and final page fields are gates before implementation. Open-Meteo is only a candidate (free endpoint currently noncommercial). Future work stays on the docket; installed behavior unchanged.

## T-025: v1.14.1 licensing/docs published

- Source notices/inventory, safe optional palette workflow and curated CC0 scene-pack builder added. Neon Pulse 8 untracked but retained locally; Git history unchanged. PixelPatterns provenance and full binary dependency/relinking review remain open.
- Five-scene README GIF uses verified CC0 layers/original Plasma/Warp and is labelled native preview. Optional archive has 16 PNGs +3 original license PDFs +README; SHA and install steps in docs/RELEASE_1.14.1.md. No firmware binary; installed firmware remains v1.14.0.
- Gemini Flash audit required correction of unsupported claims; coordinator verified correct MIT upstream sources and retained notices, fixed Git-index checking and fetch path confinement. Independent review PASS; compile/inventory/production render/archive inspection passed. Tests deferred; cost UNKNOWN.
- Published commit `0e71e0e`, tag/release [v1.14.1](https://github.com/zdhoward/AIUsageMonitor/releases/tag/v1.14.1), optional `cc0-scenes.zip` uploaded (2,539,834 bytes); public guard passed. Users extract the pack at source root and Send to display. Existing local artwork/palette/settings untouched; earlier tags retain the former palette. Firmware remains v1.14.0. Next: verify PixelPatterns at its actual source and complete binary obligations before offering prebuilt firmware/installers.

## T-024: v1.14.0 published

- Owner accepts the new wake/reset behavior and display appearance. Argon is exhausted according to owner observation, but the independent collector remains unavailable; unknown is retained. Future screensavers/transitions/audio/ticker remain on the docket.
- Studio T-020 items 1–3 implemented: Settings tab, generator sky suppression and clearer headings. New settings writes preserve unknown/private keys atomically; all POST endpoints enforce JSON and matching loopback origin/port. Corrected minutes vs seconds and brightness limits during review.
- Owner explicitly authorized release tests: 49 service + 20 Studio tests pass. Browser checks save/reload/revert/navigation and sky visibility pass with no JS errors. Main production v1.14.0 Default build and COM6 hash-verified flash pass; firmware greeting/ACKs and installed dashboard inspected. New images reviewed; docs/RELEASE_1.14.0.md records evidence/limits. Gemini Flash implemented/reviewed; Beam unavailable (free quota exhausted); independent litellm/free-review fallback PASS.
- Published main through `9411540`, tag/release [v1.14.0](https://github.com/zdhoward/AIUsageMonitor/releases/tag/v1.14.0). Public guard initially caught a synthetic test key; replaced it with a short fixture value, amended the unpushed commit, reran 20 Studio tests and guard successfully. No bypass. Remaining: independent Argon telemetry, optional T-020 items and feature backlog, portrait/Rows/logon/brightness/Wi-Fi acceptance.

## T-023: v1.13.0 installed locally

- Wrap-up: main commit `f067c9f`, local tag `v1.13.0`; no open PRs and no public push. Next: owner testing phase runs retained service tests and times near-reset saver/wake; investigate provider-side early Codex weekly reset only if it recurs using the new history. Existing Argon and T-016–T-020 backlog remains open.
- Efficiency next session: use Gemini Flash first per updated owner preference. Syntax/build checks missed two runtime regressions; keep the production payload check with nonempty cost records before flashing. Capture bounded output to local logs. Retro cost is UNKNOWN; no promotion or savings claim.

- Two-second lightweight local quota/activity reads, ten-second transcript processing, thirty-second directory discovery; aggregate cache avoids recomputation on heartbeats. Changed quotas/deadlines/activity request immediate coalesced serial pushes; network source cadences unchanged.
- `reset_warning_s` defaults to 3600: automatic Console/Details saver wakes/stays off while known available quota resets within one hour. Actual countdown stays unchanged; manual scenes/System are unaffected. Timed trigger acceptance remains pending.
- Local rotating history: `logs/quota_history.jsonl` and `.1`, only changed quota/deadline measurements; early drops flagged. No credentials/transcripts. Failed writes back off sixty seconds. Initial unseen baseline is not recorded.
- Default build and COM6 hash-verified flash passed; service restarted and reports ok=1/warn=3600/five accounts, firmware 1.13.0 and serial ACKs. Coordinator inspected `build/t023-live.png`; normal five-card dashboard. Build/flash logs: `build/t023-installed-build.log`, `build/t023-flash.log`.
- DeepSeek implementation, Beam + Gemini Flash reviews; coordinator corrected review regressions. Syntax/scope checks passed. Automated tests deferred under sprint-end policy. Cost UNKNOWN; shadow local-jev timed out/Laya abstained. No public push: GOALS requires owner publication approval. Remaining earlier backlog retained below.

## Previous handoff

## Current session: T-022 installed, Argon collection still open

- Main commits: `d28df0a` ticket, `0f76d89` 60-second default idle, `123cf9b` direct Gemini quota and pinned layout, `82d56bd` white weekly countdown below 24 hours. No open PRs (`gh pr list` returned none). No public push: GOALS requires owner publication approval. No new release tag/version; installed firmware still identifies as 1.12.0 while exact Argon work is incomplete.
- Root cause: T3's Antigravity cache reports Claude/GPT shared 3p quota. Direct read-only Google fetchAvailableModels now supplies Gemini quota using the existing T3 login; no credential/state files modified. Five-minute polling, bounded requests, in-memory token, original measurement time retained on failures. No weeklyQuotaInfo is currently returned, so weekly is unknown rather than borrowing 3p data. See service/aimon/sources/antigravity.py and docs/DATA_SOURCES.md.
- Display: A/Codex/Antigrav top, B/blank/Argon bottom. Argon is a real separate card but unknown: gemini-4-argon is absent from this token's model list. Do not substitute family quota or infer current quota from 429 logs. Exact agy gateway/quota source is the next research task; previous read-only cloudcode probes did not expose it.
- Default Console/Details idle delay is now 60 seconds; firmware fallback also 60 seconds. Grid weekly reset countdown turns white only for a known future reset below 86400 seconds; at/above a day, unknown, and due remain muted. Weekly rings and percentages keep existing colours.
- Production evidence: Default builds passed, COM6 flash hash verified, main service restarted and feeds five accounts. Coordinator inspected build/t022-console.png and build/weekly-white-live.png. Final build: 584055 bytes flash / 88608 bytes static RAM; logs build/weekly-white-build.log and build/weekly-white-flash.log. Live weekly deadlines exceed one day: highlighted state is not visually verified. Timed 60-second transition, portrait, Rows/Studio, and broader pending acceptance remain unverified. Automated tests NOT run: wrap-up does not declare sprint end under owner policy.
- Source review: Beam PASS; HIGH-risk second free-review unavailable (ECONNREFUSED), not counted as a pass. Coordinator inspected critical logic and separated Argon from family aggregate, cleared retained readings on profile change, bounded cadence/timeouts. Shadow routing capture omitted; paid cost UNKNOWN. No promotion/savings claim.
- Next concrete actions: locate exact agy Argon quota source without model requests; obtain Gemini weekly only if provider actually reports it; owner testing phase should run retained fixtures and verify <24h countdown colour, 60-second saver timing, missing-provider layout, Rows/portrait and existing due-quota saver behavior. Existing unrelated T-016 through T-020 backlog below remains open.
- Efficiency next session: read this section and T-022 first; use narrow source ranges. Record routing shadow before dispatch, and use the existing verifier for source/review evidence; do not reconstruct a large session transcript or treat unavailable review as PASS.

## Previous session (2026-10-26)

## Current session: v1.12.0 compact home

- Delivered on `main`: `3780f9a` adds the optional grid, preserves Rows, enables Default/Grid and includes Gemini/Antigravity T3 quota caches. Wrap-up commit versions this as v1.12.0. No open or thread-linked PRs. Public publication remains subject to the owner's approval rule in GOALS.md; no push in this session.
- Owner refinement: Session/5h uses the larger outer ring for detail; Weekly stays yellow on the inner ring. Both percentages and reset countdowns remain visible. Current live setup is two Claude accounts (A/B), Codex and Antigravity. No local configuration or credentials were replaced.
- Six-account capacity: 3x2 landscape, 2x3 portrait. Only the first six service accounts are stored; no paging. Future providers still need a compatible collector source. Grid uses service display names; stable account IDs remain future work.
- Evidence: successful production builds and hash-verified flashes; `build/t013-final-build.log`, `build/t013-final-flash.log`, `build/console-grid.png`. Coordinator inspected the four-account framebuffer, including 100% next to multi-day captions; owner liked the layout. Final versioned build/flash evidence is `build/v1.12.0-build.log` and `build/v1.12.0-flash.log`.
- Source review: free reviewer found unreachable paging and a calculated text-fit risk. Removed dead paging and corrected docs; actual framebuffer resolves text fit for the current 5h/7d windows. No second independent pass claimed. Automated tests remain deferred under sprint-end policy. Studio selector is wired but click/save/reload and portrait/Rows runtime checks remain pending.
- Tracking: compact-grid ticket is now [T-021](.tickets/T-021.md); dispatch/scoreboard records historically used T-013, already allocated to profiles in the index. Earlier backlog below is retained.
- Next: owner testing phase should cover Rows/Grid save/reload, portrait, six-account/unknown/stale cases and the existing due-quota saver trigger. Then consider explicit overflow handling and provider/account abbreviation configuration. Publication needs owner approval; do not bypass the public push guard. No release tests were implied by this wrap-up.

## Previous handoff: v1.11.1 (2026-10-25)

## Settings review (2026-10-25)

- `docs/SETTINGS_REVIEW.md`: every scene reviewed by local `gemma4:e4b`, checked against `scripts/settings_audit.py`. Only dead controls: sky colours on the 12 generator scenes.
- Follow-ups are [T-020](.tickets/T-020.md). The owner wants each task done in its own session to keep context small.
- Other open items: T-018 owner questions, optional full-history scan of the other public repos, delete the art backup when satisfied, sprint-end tests.

## Latest session: due-quota screensaver suppression

- Implemented and flashed **v1.11.1**, Default profile, COM6. Commit `c5d4858` and tag `v1.11.1` are pushed on `main`; no open PRs.
- `hasDueAvailableUsage` in `firmware/AIUsageMonitor/ui.cpp` checks every reported account/window using the same elapsed reset countdown as the caption. Known usage of 0–99% used with a due reset blocks automatic saving and wakes an active saver, including when usage-change waking is disabled. Unknown values and 100%-used windows do not block it.
- Validation: production build passed (583,159 bytes flash / 87,984 bytes static RAM), upload hash verified, and actual framebuffer captures inspected. `build/screensaver-build.log`, `build/screensaver-flash.log`, `build/screensaver-due.png` and `build/screensaver-dashboard.png` are local evidence. The 31-second capture showed the normal saver; live data had no qualifying due window. The final capture restored Console. These captures do **not** verify the new due trigger.
- Next: at the owner's testing phase, feed a known due window below 100% used and confirm Console/Details remain awake beyond 30 seconds and wake from an active saver. Also check unknown/100%-used exclusions and a deadline crossing. Broader existing acceptance stays open in `docs/SCREENSAVER.md`; automated tests were not run this session.
- Existing scene/audio/stock backlog is unchanged; see the previous session below and `.tickets/README.md`.

## Latest session (v1.8.0 – v1.11.0)

`main` and tags up to `v1.11.0` are **pushed** to the public GitHub repo. The owner wants it public as portfolio work, with code and the system only. Firmware 1.11.0 is flashed on COM6 with the **Default** profile, and the service is running. No open PRs. Details are in [PROJECT_LOG](docs/PROJECT_LOG.md); the owner's decisions are in [GOALS](GOALS.md).

- **Profiles (v1.11.0):** Default (Console → System → Parallax; Console sleeps to the face), Dev (all originals) and Dev (themes) (all theme shifts). Only Console is a required page. Regenerate the scene lists by rerunning the generator logic if the library changes. The Dev profiles list scenes explicitly, so new scenes must be added to them.
- **Random weather (v1.11.0):** `"weather": "random"` on a playlist (`withWeather` in `ui.cpp`, Studio checkbox in `playlists.js`). Confirmed on the display: Miami Drive got snow.
- **Long-press home:** holding for 0.7 s jumps to the Console (`uiGoHome` in `ui.cpp`, `pollTouch` in `AIUsageMonitor.ino`, `UI_HOME_PAGE`/`UI_HOLD_MS`). The owner confirmed it on the display.
- **Footer:** a link dot (green; amber when no payload for 30 s; red on a source error) plus `Updated <newest reading age>`. A stale account is shown only by its card's `STALE` label (60 min, `limits_stale_s` / `CLIENT_STALE_S`). T3 re-polls Claude quota only every few minutes; the serial link is healthy.
- **Account names:** unmatched names (the owner's T3 `A`/`B`) fill the Claude rows in order (`slotIndex`).
- **SVG (v1.9.0):** `asset_convert.py` rasterizes SVGs with `resvg-py` (`pip install resvg-py`). The Images page rotates `"image": true` manifest entries every 10 s. The owner's logo is the test case.
- **Studio UX (v1.10.0):** unsaved chip, ↑/↓ reorder, focus outlines, theme badges, library counts, auto-capture. The "display" wording is now consistent.
- **Validation:** builds at 44% flash, with display screenshots after each flash and Playwright checks of the Studio (the T3 preview snapshot times out, so use Playwright with Edge). No automated tests were run (sprint-end rule).
- **Public repo hygiene (owner rule):** no art, no personal data.
  - Art is local and git-ignored: the owner's GIF, logo, scene `src/` and previews, `assets/manifest.json`, and the generated `assets_gen.*` / `scenes_gen.*`. A clean clone builds at 33% flash: missing art is skipped, and the Images and City pages show hints.
  - The owner's location lives only in the ignored `service/aimon.config.json`; the code defaults are a Greenwich placeholder.
  - Before the first push, the 74 unpushed commits were rewritten with `git-filter-repo` (`python -m git_filter_repo`) in a scratch clone to drop art and scrub paths, username, email and location. They were then pushed as a fast-forward with no force.
  - Backup of the pre-rewrite state: the sibling folder `AIUsageMonitor-art-backup-20261025/` next to the repo (art, generated files and a git bundle). Delete it once satisfied.
- **Before each push:** scan the outgoing diff for personal paths, location, emails, keys and new art.
- **Blockers:** tests are pending sprint end.
- **Next:** hold-progress feedback (optional); a stable slot id per account from the service; flash-size gate; T-017, T-016, T-018 (audio visualizer plan, owner questions open) and T-019 (stock ticker idea).

## Previous session (v1.6.0)

`main` is tagged `v1.6.0` (local only; not pushed). Firmware 1.6.0 is flashed on COM6 with the Default profile. The service is running with the fix. No open PRs.

- **Fix:** the display had stopped updating. A Studio pause cleared the serial handle while the serial thread was writing, and the uncaught error killed that thread silently. `service/aimon/serial_link.py` now uses a local handle and catches everything.
- **System page** (`system`, after Details in the default profile) shows CPU, RAM (used/total), GPU, disk read/write and download/upload. There are no graphs, and values ease on the device.
  - `service/aimon/sysstats.py` samples with psutil, plus GPU from Windows PDH "GPU Engine" counters via ctypes.
  - The sample is sent as a separate 1 Hz `{"t":"sys",...}` line; firmware routes it in `pollSerial` to `parseSys`.
  - The page is `drawSystem` in `ui.cpp`.
- **Validation:** builds at 44% flash, and a device screenshot is in `docs/img/system-page.png`. Smooth motion is not yet confirmed by the owner. No tests were run (sprint-end rule), and no unit test covers the new sampler or the pause race.
- **Next:** confirm the easing feel (the 250 ms constant in `drawSystem`). Optionally add a regression test for pause-during-write in `service/tests`.
- **Page indicator** (`bfbfa92`): up to 6 pages show dots; beyond that `drawDots` shows a "3 / 19" counter over a thin position track. Flashed and captured on the device. Possible follow-up the owner may want: grouping pages into sections (swipe between groups, tap within one).
- **Not mine, left alone:** uncommitted `profiles/default.json` edits from another session (they were included in the last flash, so the device now has 19 pages) and the untracked `assets/img/`.

## Previous session (v1.5.0)

Delivered in v1.5.0 (details in [ASSETS](docs/ASSETS.md), [plan](docs/SCENE_LIBRARY_PLAN.md), [project log](docs/PROJECT_LOG.md)):

- **Assets:** `scripts/asset_convert.py` converts GIF/PNG/Aseprite to RLE RGB332. `anim.cpp` is the player. The Images page plays a GIF; the City page is `city.cpp`.
- **Scene engine:** `scene.cpp`, built from `scripts/scenes.py`:
  - parallax layers, effects (stars, rain, snow, lightning behind layer N), themes, theme variants and smooth theme cycles;
  - Lospec palette themes in `assets/themes/`;
  - generators: patterns, plasma, warp, matrix, fire, lava, aurora, life, ripple, fireworks, videoeq, spectre.
- **Pages:** every page is compiled in. A profile chooses the tap order, `scene:<id>` pages, up to 16 playlists (`playlist:<id>`, firmware ids 200+), the screensaver target and ring colours. Generated files: `profile_gen.h` and `playlists_gen.h` (both git-ignored).
- **Serial commands:** `!SHOW <page|scene|playlist-n>`, `!SCENES`, `!PERF`, `!TUNE <hex>|off`. The tune format is in `firmware/AIUsageMonitor/tune.h`.
- **Scene Studio** (`Scene Studio.cmd` or `python -m studio`; test instances use `--port 8799`):
  - tabs: Layout, Screensaver, Playlists, Library (gear settings, import, Lospec browser), Display;
  - previews come from the native DLL (`studio/native/build.ps1`, MSVC), at about 48 fps;
  - **Live on device** sends unsaved edits to the display.
- **Library:** 23 entries in `assets/library/`.

## Measured

- Flash use is 574 KB (43%). Static RAM is 85 KB; 184 KB heap is free during scenes.
- Scenes run at 43-68 ms per frame on the device.
- The native preview renders a frame in under 0.2 ms.

## Not done / blockers

- Automated tests: none run (owner's sprint-end rule). The service suite is `python -m unittest discover -s tests -t .` from `service/`.
- Never observed on the device: the screensaver taking over by itself (active usage keeps waking it).
- Untested: portrait rotation for scenes.
- No flash-budget gate in the build.
- `assets/gif/angry_skele.gif` has an unknown license. Confirm it before any push; the repo is public.
- Third-party packs in `assets/sprites/` are git-ignored. Only CC0 art is committed.

## Next actions

1. T-017: VJ transitions between playlist scenes, plus more effects (boids, radar, reaction-diffusion; cracktro, beams).
2. T-016: classic screensavers (3D Pipes, Maze, Mystify) as generators.
3. Port `city.cpp` onto the scene engine so the city can be edited in the Studio.
4. Add a flash-budget check to `build.ps1 -Profile`.

## Commands

- Build/flash: `scripts/build.ps1 -Profile default`, then `scripts/flash.ps1`. Convert art first with `python scripts/asset_convert.py --profile default`.
- Native preview: `powershell -File studio/native/build.ps1`.
- Capture: `python scripts/screenshot.py --out shot.png`, or the Studio's Display tab.
- Keep sessions short: this one reached a 612k-token context (see the retro in `~/.agents/retro/LOG.md`).
