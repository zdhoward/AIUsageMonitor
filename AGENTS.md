# Guide for AI agents

Read this first. It tells you how to work on this repo without breaking the user's setup or their ability to take updates. Each task has a step-by-step recipe in [docs/recipes/](docs/recipes/README.md); follow it exactly and do not improvise the order.

## What this is

A PC service (`service/`, Python) reads local AI-usage data and sends compact JSON over USB serial to an ESP32 (`firmware/AIUsageMonitor/`, C++) that only draws it. Scene Studio (`studio/`) edits profiles and scenes. Profiles (`profiles/*.json`) choose pages and settings. Build and flash with `scripts/`.

## Rules that never bend

1. **Work on the user's branch, never `main`.** Run `scripts/doctor.ps1` first. If it reports you are on `main`, switch to `my-setup` (create it if missing) before editing anything. `main` must stay identical to upstream so updates fast-forward.
2. **Prefer adding files to editing shared ones.** Make a personal profile (`profiles/my.json`) instead of editing `profiles/default.json`. Put new art under `assets/` (git-ignored). Edit a tracked file only when the recipe says so.
3. **Log every tracked file you edit** in `docs/MY_CHANGES.md` (create it on the user's branch if missing): file, what changed, why, and the date. The update recipe depends on this to resolve conflicts.
4. **Commit small and often on `my-setup`**, one change per commit, so any change can be reverted alone.
5. **Never commit or print secrets.** `service/aimon.config.json`, `firmware/AIUsageMonitor/secrets.h` and anything with keys or tokens stay local. Refer to credentials by name only.
6. **Never edit generated files.** `*_gen.*` and `profile_gen.h` are rebuilt from `profiles/`, `assets/` and `scripts/`. Change the source and rebuild.
7. **Unknown is not zero.** A missing reading shows `--`; a real 0% stays 0%. Keep last good values when data goes stale.
8. **Don't commit third-party art.** Raw art stays local. See [docs/ASSETS.md](docs/ASSETS.md).
9. **Don't run the test suite unless asked.** Prove a change works by building, flashing and showing a screenshot.

## Prove every change

```powershell
.\scripts\doctor.ps1                      # branch, remotes, secrets, config (-Maintainer allows main)
.\scripts\build.ps1 -Profile my           # compiles; use your profile name
.\scripts\flash.ps1
python scripts\screenshot.py --feed --out build\check.png   # then LOOK at the image
```

For pages beyond the first, add `--next N`. Show the user the image. If the build fails, read the first error, fix the cause and retry; do not stub things out to get it to compile.

## Where things live

| To change | Go to |
|---|---|
| A card, header or footer | `firmware/AIUsageMonitor/ui.cpp` (`drawProxy` and the `drawProxy*` helpers) |
| Which pages show, order, saver timing | `profiles/<name>.json` (validated by `scripts/profile_gen.py`) |
| Colours, thresholds, firmware switches | `firmware/AIUsageMonitor/config.h` and the palette notes in `docs/UI.md` |
| A data source | `service/aimon/sources/`, wired in `service/aimon/snapshot.py` |
| What goes over serial | `docs/PROTOCOL.md`, `service/aimon/snapshot.py`, `firmware/AIUsageMonitor/model.cpp` |
| Scenes and art | `docs/ASSETS.md`, Scene Studio (`Scene Studio.cmd`) |
| Display driver, pins | the `$tft` flags in `scripts/build.ps1` |

## Recipes

- [Customise safely and take updates](docs/recipes/customise-safely.md)
- [Update to the latest release](docs/recipes/update.md)
- [Add a card to the Proxy page](docs/recipes/add-card.md)
- [Add a screensaver scene](docs/recipes/add-scene.md)
- [Add a data source](docs/recipes/add-data-source.md)
- [Fit a different screen size](docs/recipes/resize-display.md)

## If you are a small or weaker model

Do one recipe step at a time. After each step, run the check the recipe names before moving on. If a check fails, stop and fix it; do not continue. If a step does not match what you see in the files, stop and tell the user rather than guessing.
