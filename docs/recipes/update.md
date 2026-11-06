# Update to the latest release

Goal: bring in upstream changes, keep your customisations, and end with a working display.

Do the steps in order. Stop and ask the user if a conflict touches `firmware/AIUsageMonitor/ui.cpp` and you cannot tell what both sides intended.

1. **Check state.** Run `.\scripts\doctor.ps1`. You must be on `my-setup` with a clean tree. If the tree is dirty, commit your work first (`git add -A` then `git commit -m "Save work before update"`).
2. **Make a rollback point.** `git tag backup/pre-update-$(Get-Date -Format yyyyMMdd-HHmm)`. Rolling back later is `git reset --hard <that tag>` on `my-setup`.
3. **Fetch.** `git fetch origin --tags`.
4. **Read what changed.** `git log --oneline my-setup..origin/main` and read any new `docs/RELEASE_*.md`. Note anything about config keys, profile fields or hardware.
5. **Fast-forward main.** `git switch main`, then `git merge --ff-only origin/main`. If this fails, `main` holds your commits: stop, follow "If you already edited `main`" in [customise-safely](customise-safely.md), then return here.
6. **Merge into your branch.** `git switch my-setup`, then `git merge main`.
   - No conflicts: continue.
   - Conflicts: run `git status` to list them. For each file, open `docs/MY_CHANGES.md` to see what your change was for, then keep both intents (upstream's new code plus your edit). Never discard upstream's side wholesale. Finish with `git add <file>` and `git commit`.
7. **Check config.** Compare `service/aimon.config.example.json` with your `service/aimon.config.json`; add any new keys you are missing (never overwrite your values). Do the same for `profiles/default.json` against `profiles/my.json` if the release notes mention new profile fields.
8. **Install dependencies.** `python -m pip install -r service/requirements.txt`.
9. **Rebuild and flash.** `.\scripts\build.ps1 -Profile my`, then `.\scripts\flash.ps1`.
10. **Restart the service.** `.\scripts\service.ps1 stop` then `.\scripts\service.ps1 start`, then `.\scripts\service.ps1 status`.
11. **Prove it.** `python scripts\screenshot.py --feed --out build\after-update.png` and look at the image. Show the user.
12. **Record it.** Add a line to `docs/MY_CHANGES.md` for any file whose conflict you resolved, and commit.

If anything fails and you cannot fix the cause quickly, roll back with the tag from step 2, rebuild, and tell the user what failed.
