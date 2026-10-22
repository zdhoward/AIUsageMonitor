# Public release preparation

The owner selected the MIT license and requested local preparation for review on 2026-10-22. The GitHub repository remains private; no push, visibility change or GitHub release is authorized by this preparation step.

## Prepared

- MIT [license](../LICENSE), attributed to Zach Howard.
- Current dashboard framebuffer image: [v1.4.2](img/v1.4.2-rings.png). This is rendered on the actual device, not a photograph or mockup. It shows subscription percentages and reset durations, without account emails or credentials.
- Hardware pinout, build/setup instructions, data-source limitations and contributor guidance.
- Source and history secret scan using Gitleaks, with full redaction. The pre-documentation `main` scan covered 24 commits and reported no leaks. A final scan is recorded in the project log after integration. This is a scanner result, not a guarantee of absence.
- Generated builds, logs, local service configuration and Wi-Fi credentials are excluded by `.gitignore`.

## Owner review before publication

1. Read the README and hardware reference, and review the screenshot as the public portfolio image.
2. Review Git history as well as current files. Earlier commits include a board MAC address and local Windows paths in development documentation; removing them from the current documentation does not remove them from history. No history rewrite was performed. Decide whether that historical detail is acceptable before publishing.
3. Confirm the public project name, description and repository topics. Suggested description: “An ESP32 desktop dashboard for AI subscription quotas, reset countdowns and local usage telemetry.” Suggested topics: `esp32`, `arduino`, `python`, `dashboard`, `embedded`, `usage-monitor`.
4. Check third-party dependencies under their own licenses. This project's MIT license applies to its own code and documentation; dependencies are installed separately and are not relicensed here.
5. Explicitly authorize pushing local commits/tags and making the repository public. No remote settings were changed during preparation.

## Known limits to retain publicly

- Tested hardware is one ESP32-2432S024C variant with ILI9341 and CST820; similarly named boards may differ.
- Windows PowerShell tooling is the tested setup. Optional Wi-Fi has not been exercised on hardware.
- T3 cache/database and local transcript formats are integration details, not stable public provider APIs.
- A reset deadline causes a local cache/transcript reread. It does not force a provider request or assume quota has refilled.
- Physical viewing distance, tap reliability, unplug/replug, PC sleep and actual logon-task execution are not proven by framebuffer captures.
