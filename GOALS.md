# Accepted display decisions

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

- MIT license, selected 2026-10-22. Prepare documentation locally for owner review; keep GitHub private and do not push or publish yet.
- README uses the actual current dashboard framebuffer as the portfolio image. Document implemented pinout, reproducible setup and verified limitations.

No implementation request is pending. Owner review of the public documentation and historical machine identifiers remains before publication. Source/configuration are authoritative for implementation values; [docs/UI.md](docs/UI.md) explains the renderer.
