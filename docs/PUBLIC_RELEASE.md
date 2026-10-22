# Public release preparation

The owner selected the MIT license, then explicitly requested the completed repository be pushed and made public on 2026-10-22. GitHub now reports [zdhoward/AIUsageMonitor](https://github.com/zdhoward/AIUsageMonitor) as public.

## Prepared

- MIT [license](../LICENSE), attributed to Zach Howard.
- Current dashboard framebuffer image: [v1.4.2](img/v1.4.2-rings.png). This is rendered on the actual device, not a photograph or mockup. It shows subscription percentages and reset durations, without account emails or credentials.
- Hardware pinout, build/setup instructions, data-source limitations and contributor guidance.
- Source and history secret scan using Gitleaks, with full redaction. The integrated scan covered the 26 `main` commits through `3700cd0`; the subsequent `a7f2dd7` release record was separately scanned while staged. Neither scan reported leaks. This is scanner evidence, not a guarantee of absence.
- Generated builds, logs, local service configuration and Wi-Fi credentials are excluded by `.gitignore`.
- Repository description is “An ESP32 dashboard for AI subscription quotas, reset countdowns, and local usage telemetry.” Topics: `esp32`, `arduino`, `python`, `dashboard`, `embedded`, `usage-monitor`.

## Publication record

- Pushed `main` through `a7f2dd7`; remote and local branch were verified synchronized.
- Visibility was changed from private to public and verified through GitHub.
- No history rewrite was performed. Earlier commits still contain a board MAC address and local Windows paths in development documentation. They are not credentials; the historical exposure is documented so maintainers understand what the public history contains.
- Third-party dependencies retain their own licenses; MIT applies to this project's code and documentation.

## Known limits to retain publicly

- Tested hardware is one ESP32-2432S024C variant with ILI9341 and CST820; similarly named boards may differ.
- Windows PowerShell tooling is the tested setup. Optional Wi-Fi has not been exercised on hardware.
- T3 cache/database and local transcript formats are integration details, not stable public provider APIs.
- A reset deadline causes a local cache/transcript reread. It does not force a provider request or assume quota has refilled.
- Physical viewing distance, tap reliability, unplug/replug, PC sleep and actual logon-task execution are not proven by framebuffer captures.
