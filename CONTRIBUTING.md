# Contributing

Start with the [setup guide](docs/SETUP.md), [hardware reference](docs/HARDWARE.md) and [UI design](docs/UI.md). The tested platform is Windows plus the documented ESP32-2432S024C variant. State your board/controller and toolchain versions when reporting hardware issues.

Keep changes focused and explain the user-visible behavior. Separate collection, transport, model caching and rendering. Preserve unknown-versus-zero semantics, last measured values during stale data, and independent Session/Weekly windows. A passed reset deadline is not proof of quota refill.

## Validate changes

- Service behavior: run the relevant fixture tests, then `python -m unittest discover -s tests -t .` from `service/` for a completed milestone.
- Firmware: run `scripts/build.ps1`; for renderer changes, flash the actual board and attach a framebuffer capture using `scripts/screenshot.py`.
- Documentation: check local links, commands and version claims against source. Mark untested compatibility as untested.
- Use `git diff --check` before committing. Describe what ran and its limits; a framebuffer does not prove physical touch reliability or viewing comfort.

Do not commit account caches, transcripts, databases, API keys, Wi-Fi secrets, generated builds or local configuration. Use synthetic fixtures and review screenshots/logs for personal information. Existing ignore rules cover build/log folders, `secrets.h` and `aimon.config.json`.

Contributions are accepted under the project's [MIT license](LICENSE); third-party dependencies keep their own licenses. Please report potential vulnerabilities without posting usable credentials or private account data in a public issue.
