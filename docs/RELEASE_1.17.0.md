# v1.17.0 — Safe updates and AI-agent guides

No firmware change: nothing to reflash. Pull, then restart Scene Studio to load the new tab.

- **Keep your changes and still get updates.** The setup prompt now puts customisations on a `my-setup` branch with a personal `profiles/my.json`, while `main` stays identical to this repository. Taking a release is a merge, after a backup tag, so it can be undone in one command. No fork is needed.
- **Updates tab in Scene Studio.** Check for a newer release, see what changed, and see before committing whether it would overlap your edits (a trial merge that changes nothing). Update now tags a backup, merges and installs Python packages. A conflict is aborted cleanly and Studio hands you a prompt for your AI agent. Buttons to rebuild and flash, restart the service and undo the last update follow. A dot on the tab shows when a release is waiting.
- **Guides for AI agents.** `AGENTS.md` holds the rules and a map of the project (`CLAUDE.md` and `GEMINI.md` point to it). `docs/recipes/` has step-by-step recipes written for small models: customise safely, update, add a card, add a scene, add a data source, fit another screen size.
- **`scripts/doctor.ps1`** checks the branch, upstream, tracked secrets, config and tools before and after a change (`-Maintainer` allows working on `main`).
- Fixed: a failed update no longer leaves a backup tag that "Undo" would land on. Added tests for the proxy `tz` field.

## Verification

- Service suite 56 tests, Studio suite 29 tests (nine cover the updater against scratch git repos) and the third-party check all pass.
- The Updates tab was checked in a browser in its idle state. The update-available and conflict panels, the setup prompt on a clean checkout, and the resize recipe on boards other than 320x240 are not yet exercised.
