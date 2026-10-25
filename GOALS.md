# Accepted display decisions

## Profiles and wording (2026-10-25)

- **Wording:** the hardware is "the display" in the UI and user docs. "Device" is only for hardware/technical contexts (USB detection, reboot).
- **Profiles** (`profiles/`):
  - **Default:** Console → System → Parallax, no Details. The Console sleeps to the Companion face. System and Parallax never sleep. The Parallax playlist cycles the layered scenes (Miami Drive, Neon Skyline, Rainy Street), with random weather per scene turn: clear, rain, snow or storm.
  - **Dev:** every page and the original of every scene, with no screensaver.
  - **Dev (themes):** Console, Details, a theme-shift playlist and every theme-shift scene, with no screensaver.
- Only the Console page is required (it is the long-press home). Details is optional.
- **Pushing:** push completed work at milestones. Private repos need no confirmation; this repo is public, so anything newly public needs the owner's OK first.

## Automatic brightness (2026-10-24)

- Owner requested configurable daylight brightness and selected the owner's city. PC service fetches/caches SunriseSunset.io schedules; ESP applies PWM targets across every view without waking idle views.
- Installed defaults: day 255, night 40, startup fallback 80, 60-minute centred sunrise/sunset transitions and 1000ms device interpolation. Settings and failure behavior: [brightness guide](docs/BRIGHTNESS.md). Physical comfort and broader acceptance remain pending.

## Current display state (2026-10-23)

- The Console and Details dashboards remain the quota views. Companion and Images are optional additional views; Screensaver is automatic presentation and is not a navigation stop.
- Console and Details default to separate 30-second idle timers and wake on measured usage changes. Each has build-time enable, timeout and wake settings. Companion/Images never sleep. See [UI](docs/UI.md) and [Screensaver acceptance](docs/SCREENSAVER.md).
- T-010 default idle/wake behavior is built and flashed with framebuffer evidence. Sprint-end tests and broader touch/configuration/renderer acceptance remain pending. No new release tag is implied.

Final user choices from 2026-10-22; these supersede earlier portrait/bar/extra-page concepts.

- Default landscape (rotation 1), attached beneath a monitor and read at a glance.
- Exactly two views toggled by tapping: clean console and original details.
- Three stable providers: Claude A, Claude B, Codex.
- Two rings per provider: Session left, Weekly right. Show quota remaining, preserve window identity, keep weekly yellow and session capacity colors.
- Shared Session/Weekly column headers. Group `AI USAGE (3 CLIENTS)` on the left. Ring captions show large, bright reset countdowns; rings sit higher to make room.
- Keep the area under provider titles empty until the user requests content there. T3 is available for detailed information.
- Keep last known values bright during stale/missing data, while visibly reporting freshness. Unknown differs from zero; a reset deadline does not imply a refill.
- Keep animation restrained and the renderer easy for a future Claude pass to modify.
- Practical verification: build, run, inspect the display. Avoid expanding the test suite for visual refinements.

## Public project decisions

- MIT license, selected 2026-10-22. Documentation and framebuffer published to the public GitHub portfolio repository on 2026-10-22 at the user's direction.
- README uses the actual current dashboard framebuffer as the portfolio image. Document implemented pinout, reproducible setup and verified limitations.

## MINT decisions (2026-10-23)

- Use Grobot as the practical starting engine; keep the adapter thin and replaceable. Prioritize simplicity, smooth movement and table-driven emotion growth.
- Companion displays facial features across the full canvas: eyes, mouth and occasional effects; no permanent body or enclosure.
- PC service owns mood, reaction priority and optional CPU/RAM awareness; firmware owns smooth rendering and safe state expiry. Preserve the existing sole serial owner.
- See [MINT](docs/MINT.md) and [T-009](.tickets/T-009.md) for implementation and remaining validation.

Historical board/local-machine identifiers remain in earlier commits and are disclosed in the release record. Source/configuration are authoritative for implementation values; [docs/UI.md](docs/UI.md) explains the renderer.
