---
id: T-007
title: Prepare public README, setup and hardware documentation
task_type: docs
lane: implement
critical: false
files:
  - README.md
  - docs/HARDWARE.md
  - docs/SETUP.md
  - docs/PROTOCOL.md
  - CONTRIBUTING.md
acceptance:
  - git diff --check
---

## Goal
Make this small ESP32/Python dashboard reproducible and portfolio-ready for a public GitHub audience. Documentation only; no source, script, license, release or remote changes.

## Context
Firmware v1.4.2 is built/flashed. The actual current framebuffer is docs/img/v1.4.2-rings.png; show it prominently near the top of README with meaningful alt text and an honest framebuffer caption. Existing details screenshot can be supplementary with its historical version stated. Default landscape rotation 1. Two tap-cycled views; Session/Weekly rings show remaining quota. Reset captions are now bright font 2, rings moved up 6px. Deadlines cause cache/transcript reread, NOT forced provider refresh. No credentials on device. Current three rows map CL1/CL2/Codex; document customization honestly. Windows scripts are tested; don't promise cross-platform scripts. T3 private cache/database formats may change. Optional Wi-Fi untested. Pinout must match build.ps1, config.h and AIUsageMonitor.ino: TFT 12/13/14/15/2, reset -1, backlight 27; touch SDA33 SCL32 RST25, address 0x15; INT21 historical wiring and unused by firmware. No external wiring required on integrated board. Remove unique MAC, personal paths and narratives about previous private sketches from HARDWARE.md. Retain provenance as board-specific local hardware verification, distinguish observed facts/assumptions. Do not invent universal board compatibility or physical pin connector numbers.

## Steps
1. Read relevant source and scripts, existing docs. Rewrite README into a concise project overview: motivation, screenshot, capabilities, architecture, hardware/BOM/pinout summary, quick start links, limitations, documentation index. Keep detailed setup in docs/SETUP.md. No license claim pending owner choice.
2. Document fresh-machine install prerequisites with tested versions (Python 3.13, pyserial, Arduino CLI 1.2.0, ESP32 3.3.1, TFT_eSPI 2.5.43, ArduinoJson 7.4.2); dependency installation commands, ESP32 board index, scripts, configuration, provider names, troubleshooting and screenshot command. Verify command syntax against installed CLI help or local evidence; avoid network and external source browsing. Mark version pins as tested baseline. Explain no accounts yields unknowns, and price table dependency. No bb_captouch dependency: firmware uses Wire directly.
3. Rewrite hardware doc with complete implemented pinout, active-high PWM backlight, buses/frequencies, touch polling vs unused interrupt, USB/serial/power assumptions and board variant warning. No precise power current claim without evidence.
4. Add protocol/API doc grounded in model.cpp, snapshot.py and server.py, with synthetic non-secret example, unknown vs zero/stale semantics, serial commands including !SHOT binary frame details and localhost routes. API is unauthenticated localhost, optional LAN exposure needs trusted network.
5. Add concise CONTRIBUTING.md: reproduce, test/build commands, board-specific renderer validation, credential/private-data exclusions, no unsupported compatibility claims.

## Done when
Only allowed files changed; git diff --check passes. Return changed files, verified facts, uncertainties, and commit SHA. Commit the documentation as one meaningful piece. Do not publish, push, tag, alter global config or delegate further.
