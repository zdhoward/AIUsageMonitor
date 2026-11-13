# Customise safely

Goal: your changes live on your own branch, your data stays out of Git, and a new release merges in cleanly.

## The model

- `main` is a mirror of upstream. You never edit it.
- `my-setup` is your branch. Everything you change is committed here.
- Personal data (`service/aimon.config.json`, `secrets.h`, art under `assets/`) is already git-ignored, so it never conflicts.
- Only edits to **tracked** files can conflict on update. Keep those few and small, and log them.

You do not need a fork. Clone, branch, work. If you want an off-machine backup, add your own private repo as a second remote (step 5).

## Steps

1. **Check the start state.** Run `.\scripts\doctor.ps1`. Expect a warning about `main` or a missing profile; that is fine.
2. **Create your branch.** `git switch -c my-setup`. Check: `git branch --show-current` prints `my-setup`.
3. **Create your profile.** Copy `profiles/default.json` to `profiles/my.json` and edit the copy (pages, order, screensaver); an unchanged copy is also valid. Never edit `default.json`. Check: `python scripts\profile_gen.py my` exits with code 0 and prints `wrote ...profile_gen.h`. `skipped (missing src/...)` and `art not installed` warnings are expected when your art is not installed. Then always build with `.\scripts\build.ps1 -Profile my`.
4. **Create the ledger.** Create `docs/MY_CHANGES.md` with the heading `# My changes` and a table with columns File, What and why, Date. Commit it with the profile: `git add profiles/my.json docs/MY_CHANGES.md` then `git commit -m "Add my profile and change ledger"`.
5. **Optional backup.** Create an empty **private** repository on your own account, then `git remote add backup <its URL>` and `git push -u backup my-setup`. Do not push to `origin`; it is upstream.
6. **Re-run `doctor.ps1`.** It should report branch `my-setup` and no FAIL lines.

## Day to day

- One change, one commit, on `my-setup`.
- Before editing a tracked file, ask whether a new file would do (a new profile, a new scene, a new source file). If you must edit it, add a row to `docs/MY_CHANGES.md` in the same commit.
- Keep edits to shared files small. Put new code in new functions or new files and make the shared file only call it. Small, additive edits merge cleanly.

## If you already edited `main`

Do not reset. Run `git switch -c my-setup` (this keeps your uncommitted work), commit there, then restore `main` with `git switch main` followed by `git reset --hard origin/main`. Only run that reset after confirming `git log origin/main..my-setup` lists your commits, so nothing is lost.
