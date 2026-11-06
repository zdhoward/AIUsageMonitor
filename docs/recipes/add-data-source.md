# Add a data source

A source is a Python module in `service/aimon/sources/` that reads a tool's usage and returns plain numbers. The snapshot builder calls it on a schedule and folds the result into the payload the display receives.

Read first: [DATA_SOURCES.md](../DATA_SOURCES.md) and [PROTOCOL.md](../PROTOCOL.md). Model files: `service/aimon/sources/openrouter.py` (a polled API) and `service/aimon/sources/opencode_db.py` (a local database).

## Rules

- Read-only. Never modify another tool's files or refresh its logins.
- Never print, log or send credentials. Read keys from environment variables or git-ignored files and refer to them by name.
- Unknown is not zero. If a reading is unavailable, report it as unknown and keep the last good value as stale.
- Never force a provider request that the tool would not already make, unless the user agreed.

## Steps

1. **Pick the shape.** Does the source report a quota (percent left with a reset time) or activity (tokens, cost, requests)? Quotas become tiles; activity goes in the Details data.
2. **Write the module.** Create `service/aimon/sources/<name>.py` with one function that takes what it needs (paths, a timeout) and returns a small dataclass or dict. Catch errors inside and return an "unavailable" result with a short reason; never raise into the poller.
3. **Add settings.** In `service/aimon/config.py` add a refresh interval and any path or switch, with a safe default. Add the same keys, disabled or empty, to `service/aimon.config.example.json`.
4. **Wire it.** In `service/aimon/snapshot.py`, import the module, add a `_next_<name>` timer beside `_next_opencode`, and call your function through the same `guarded("<name>", ...)` wrapper the others use, so a failure cannot stop the loop.
5. **Put it in the payload.** Add your fields to the dict `snapshot.py` builds. Keep names short (serial is limited) and document each field in `docs/PROTOCOL.md`.
6. **Show it.** For a new tile or card, follow [add a card](add-card.md); the firmware reads the field in `firmware/AIUsageMonitor/model.cpp`.
7. **Run it.** `.\scripts\service.ps1 stop`, `.\scripts\service.ps1 start`, then `.\scripts\service.ps1 status`. Check: the status shows your source and no error.
8. **Look.** Rebuild, flash and capture with `python scripts\screenshot.py --feed --out build\source.png`. Show the user.
9. Add the ledger row for every tracked file you edited.

## Common mistakes

- Letting an exception escape the source: wrap it with `guarded`.
- Reporting a failed read as 0%: report unknown.
- Putting a key in the example config: use a placeholder name only.
