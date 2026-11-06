"""Update flow for Scene Studio: the git steps of docs/recipes/update.md as code.

Customisations live on a branch (usually `my-setup`); `main` mirrors upstream
(`origin`). Updating tags a backup, fast-forwards `main`, then merges it into
the current branch. A conflicting merge is aborted so the tree is never left
half-merged; the caller gets the conflicted file names instead.

Every function takes the repo root so tests can run against a scratch repo.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

BACKUP_PREFIX = "backup/pre-update-"
UPSTREAM = "origin"
TRUNK = "main"
Log = Callable[[str], None]


def git(root: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
    return subprocess.run(
        ["git", "-c", "core.quotepath=off", *args], cwd=root, env=env, capture_output=True, text=True,
        errors="replace", timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _out(root: Path, *args: str) -> str:
    r = git(root, *args)
    return r.stdout.strip() if r.returncode == 0 else ""


def fetch(root: Path) -> str:
    """Fetch upstream with tags. Returns an error message, or '' on success."""
    try:
        r = git(root, "fetch", UPSTREAM, "--tags", "--quiet", timeout=60)
    except subprocess.TimeoutExpired:
        return "Timed out reaching GitHub."
    return "" if r.returncode == 0 else (r.stderr.strip().splitlines() or ["git fetch failed"])[-1]


def backups(root: Path) -> list[str]:
    out = _out(root, "tag", "--list", f"{BACKUP_PREFIX}*", "--sort=-creatordate")
    return out.splitlines() if out else []


def _conflicts_preview(root: Path) -> list[str] | None:
    """Files that would conflict if upstream merged now; None when git is too old to say."""
    r = git(root, "merge-tree", "--write-tree", "--name-only", "--no-messages", "HEAD", f"{UPSTREAM}/{TRUNK}")
    if r.returncode == 0:
        return []
    if r.returncode != 1:
        return None
    lines = r.stdout.splitlines()[1:]  # first line is the result tree id
    files = []
    for line in lines:
        if not line.strip():
            break
        files.append(line.strip())
    return files


def status(root: Path, check: bool = False) -> dict:
    """Snapshot of where this checkout stands against upstream. `check` fetches first."""
    fetch_error = fetch(root) if check else ""
    branch = _out(root, "rev-parse", "--abbrev-ref", "HEAD")
    porcelain = git(root, "status", "--porcelain").stdout  # not stripped: lines start with a status column
    dirty_files = [ln[3:] for ln in porcelain.splitlines() if ln.strip()]
    have_up = git(root, "rev-parse", "--verify", "--quiet", f"{UPSTREAM}/{TRUNK}").returncode == 0
    pending = _out(root, "log", "--format=%h %s", "-n", "30", f"HEAD..{UPSTREAM}/{TRUNK}").splitlines() if have_up else []
    behind = int(_out(root, "rev-list", "--count", f"HEAD..{UPSTREAM}/{TRUNK}") or 0) if have_up else 0
    trunk_ahead = int(_out(root, "rev-list", "--count", f"{UPSTREAM}/{TRUNK}..{TRUNK}") or 0) if have_up else 0
    s = {
        "branch": branch,
        "on_trunk": branch == TRUNK,
        "version": _out(root, "describe", "--tags", "--abbrev=0", "--match", "v*", "HEAD"),
        "upstream_version": _out(root, "describe", "--tags", "--abbrev=0", "--match", "v*", f"{UPSTREAM}/{TRUNK}") if have_up else "",
        "commit": _out(root, "rev-parse", "--short", "HEAD"),
        "dirty": dirty_files,
        "behind": behind,
        "pending": pending,
        "trunk_ahead": trunk_ahead,
        "conflicts": _conflicts_preview(root) if behind else [],
        "backups": backups(root)[:5],
        "fetch_error": fetch_error,
        "checked": check and not fetch_error,
        "has_upstream": have_up,
    }
    s["blocker"] = _blocker(s)
    return s


def _blocker(s: dict) -> str:
    if not s["has_upstream"]:
        return "No upstream found. Run a check while online, or confirm the `origin` remote is the project repository."
    if s["trunk_ahead"]:
        return ("Your local `main` has commits that are not upstream. Move them to your own branch first "
                "(see docs/recipes/customise-safely.md).")
    if s["branch"] == "HEAD":
        return "You are on a detached HEAD. Switch to your branch first."
    return ""


def apply(root: Path, log: Log, commit_first: bool = False) -> dict:
    """Run the update. Returns {ok, error?, conflicts?, backup?, merged?}."""
    s = status(root)
    if s["blocker"]:
        return {"ok": False, "error": s["blocker"]}
    if s["dirty"]:
        if not commit_first:
            return {"ok": False, "error": "You have uncommitted changes. Save them first, or tick 'Save my changes first'."}
        log("Saving your uncommitted changes\n")
        git(root, "add", "-A")
        r = git(root, "commit", "-m", "Save work before update")
        if r.returncode != 0:
            return {"ok": False, "error": "Could not save your changes: " + (r.stderr.strip() or r.stdout.strip())[-300:]}

    tag = BACKUP_PREFIX + time.strftime("%Y%m%d-%H%M%S")
    git(root, "tag", tag)
    log(f"Backup tag {tag}\n")

    err = fetch(root)
    if err:
        return {"ok": False, "error": err, "backup": tag}
    log("Fetched upstream\n")

    branch = s["branch"]
    if branch == TRUNK:
        r = git(root, "merge", "--ff-only", f"{UPSTREAM}/{TRUNK}")
    else:
        ff = git(root, "fetch", UPSTREAM, f"{TRUNK}:{TRUNK}")  # fast-forwards local main, refuses otherwise
        if ff.returncode != 0:
            return {"ok": False, "backup": tag, "error": "Could not fast-forward `main`: " + (ff.stderr.strip() or "unknown error")[-300:]}
        log("main is up to date with upstream\n")
        r = git(root, "merge", "--no-edit", TRUNK)
    log(r.stdout)
    if r.returncode != 0:
        files = _out(root, "diff", "--name-only", "--diff-filter=U").splitlines()
        git(root, "merge", "--abort")
        log("Merge stopped and undone: your files are as they were.\n")
        if files:
            return {"ok": False, "conflicts": files, "backup": tag,
                    "error": "Your changes overlap with the update in: " + ", ".join(files)}
        return {"ok": False, "backup": tag, "error": "Merge failed: " + (r.stderr.strip() or r.stdout.strip())[-300:]}

    log("Merged\n")
    req = root / "service" / "requirements.txt"
    if req.is_file():
        log("Installing Python packages\n")
        p = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)], cwd=root,
                           capture_output=True, text=True, errors="replace", timeout=600,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if p.returncode != 0:
            log(p.stderr[-500:])
            return {"ok": True, "backup": tag, "warning": "Updated, but installing Python packages failed. See the log."}
    return {"ok": True, "backup": tag}


def rollback(root: Path) -> dict:
    """Return the current branch to its most recent pre-update backup tag."""
    tags = backups(root)
    if not tags:
        return {"ok": False, "error": "No backup found."}
    if _out(root, "status", "--porcelain"):
        return {"ok": False, "error": "Save or discard your uncommitted changes first."}
    tag = tags[0]
    r = git(root, "reset", "--hard", tag)
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr.strip() or "reset failed")[-300:]}
    return {"ok": True, "backup": tag, "next": "Rebuild and flash, then restart the service, to match the restored code."}


AGENT_PROMPT = (
    "Update AI Usage Monitor by following docs/recipes/update.md exactly. A previous automatic update "
    "stopped on conflicts in: {files}. Read docs/MY_CHANGES.md to see what each of my edits was for, "
    "keep both my change and upstream's, rebuild and flash, then show me a framebuffer capture. "
    "Ask me before discarding anything."
)


def agent_prompt(files: list[str]) -> str:
    return AGENT_PROMPT.format(files=", ".join(files) or "unknown files")
