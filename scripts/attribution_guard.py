"""Block AI contributor attribution without changing legitimate human credits.

Usage: python scripts/attribution_guard.py install
       python scripts/attribution_guard.py check [REVISION_RANGE]
       python scripts/attribution_guard.py prepare SOURCE NEW_BRANCH

Prepare makes a separate cleaned branch, preserving trees and identity metadata.
It never changes existing branches, tags, remotes, or the working tree.
"""
import argparse
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
AI = re.compile(
    r"\b(?:claude|anthropic|codex|openai|gemini|copilot|cursor|"
    r"t3\s*code|gpt[-\s]?\d|ai\s+assistant)\b", re.I
)
CREDIT = re.compile(rb"(?im)^\s*co-authored-by\s*:\s*([^\r\n]*)\r?$\n?")
MARKER = "# AIUsageMonitor attribution guard"


def git(*args, data=None):
    return subprocess.run(
        ["git", *args], cwd=ROOT, input=data, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    ).stdout


def ai_credit(value):
    return bool(AI.search(value.decode("utf-8", errors="replace")))


def clean_message(message):
    return CREDIT.sub(lambda m: b"" if ai_credit(m[1]) else m[0], message)


def check_message(message):
    if clean_message(message) != message:
        raise ValueError("AI co-author credit rejected; remove the AI Co-Authored-By trailer")


def check_commit(sha):
    raw = git("cat-file", "commit", sha)
    headers, message = raw.split(b"\n\n", 1)
    for line in headers.splitlines():
        if line.startswith((b"author ", b"committer ")) and ai_credit(line):
            raise ValueError(f"{sha[:12]}: AI author/committer rejected")
    try:
        check_message(message)
    except ValueError as exc:
        raise ValueError(f"{sha[:12]}: {exc}") from exc


def check_range(revision):
    commits = git("rev-list", revision, "--").decode().splitlines()
    for sha in commits:
        check_commit(sha)
    print(f"Attribution OK: {len(commits)} commit(s)")


def hooks_dir():
    return Path(git("rev-parse", "--path-format=absolute", "--git-path", "hooks").decode().strip())


def install():
    hooks = hooks_dir()
    hooks.mkdir(parents=True, exist_ok=True)
    script = shlex.quote(Path(__file__).resolve().as_posix())
    for name in ("commit-msg", "pre-push"):
        path = hooks / name
        previous = hooks / (name + ".before-attribution")
        if path.exists() and MARKER not in path.read_text(encoding="utf-8"):
            if previous.exists():
                raise ValueError(f"Refusing to overwrite existing hook backup: {previous.name}")
            path.rename(previous)
        path.write_text(
            f'#!/bin/sh\n{MARKER}\nexec python {script} hook {name} "$@"\n',
            encoding="utf-8", newline="\n",
        )
        path.chmod(path.stat().st_mode | 0o111)
    print("Installed commit-msg and pre-push guards; existing hooks retained and chained")


def hook(name, args):
    payload = sys.stdin.buffer.read() if name == "pre-push" else None
    previous = hooks_dir() / (name + ".before-attribution")
    # Run any existing hook first; commit-msg hooks can alter the message.
    if previous.exists():
        shell = shutil.which("sh")
        if not shell:
            # Git for Windows bundles sh, but does not always put it on PATH.
            candidate = Path(shutil.which("git") or "git").resolve().parent.parent / "bin/sh.exe"
            if not candidate.is_file():
                raise ValueError("Cannot locate sh to run the existing hook")
            shell = str(candidate)
        result = subprocess.run([shell, previous.as_posix(), *args], cwd=ROOT, input=payload)
        if result.returncode:
            return result.returncode
    if name == "commit-msg":
        check_message(Path(args[0]).read_bytes())
    else:
        for line in payload.decode().splitlines():
            _, local, _, remote = line.split()
            if set(local) == {"0"}:  # ref deletion
                continue
            if set(remote) == {"0"}:
                # A new branch must not reintroduce dirty historical commits.
                check_range(local)
            else:
                check_range(f"{remote}..{local}")
    return 0


def prepare(source, branch):
    ref = "refs/heads/" + branch
    git("check-ref-format", ref)
    existing = subprocess.run(["git", "show-ref", "--verify", "--quiet", ref], cwd=ROOT)
    if existing.returncode != 1:
        raise ValueError("Cleanup branch already exists or cannot be checked")
    commits = git("rev-list", "--reverse", "--topo-order", source, "--").decode().splitlines()
    mapping = {}
    removed = 0
    for sha in commits:
        raw = git("cat-file", "commit", sha)
        headers, message = raw.split(b"\n\n", 1)
        if b"\ngpgsig " in headers or b"\nmergetag " in headers:
            raise ValueError("Signed history needs explicit signature handling; no branch created")
        clean = clean_message(message)
        removed += len(CREDIT.findall(message)) - len(CREDIT.findall(clean))
        lines = []
        for line in headers.split(b"\n"):
            if line.startswith(b"parent "):
                line = b"parent " + mapping[line[7:].decode()].encode()
            lines.append(line)
        rewritten = b"\n".join(lines) + b"\n\n" + clean
        new_sha = git("hash-object", "-t", "commit", "-w", "--stdin", data=rewritten).decode().strip()
        # Verify everything except parent links and removed AI trailers byte-for-byte.
        verified = git("cat-file", "commit", new_sha)
        if verified != rewritten:
            raise ValueError("Rewritten commit failed byte verification")
        check_commit(new_sha)
        mapping[sha] = new_sha
    tip = git("rev-parse", source + "^{commit}").decode().strip()
    git("update-ref", ref, mapping[tip], "0" * len(tip))
    print(f"Prepared {branch}: {len(commits)} commits verified, {removed} AI trailers removed")
    print("All file trees, human credits, author/committer identities and dates preserved")
    print("Existing branches, tags and remote history unchanged")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install")
    check = sub.add_parser("check")
    check.add_argument("revision", nargs="?", default="HEAD")
    prep = sub.add_parser("prepare")
    prep.add_argument("source")
    prep.add_argument("branch")
    hooks = sub.add_parser("hook")
    hooks.add_argument("name", choices=("commit-msg", "pre-push"))
    hooks.add_argument("args", nargs="*")
    args = parser.parse_args()
    try:
        if args.command == "install":
            install()
        elif args.command == "check":
            check_range(args.revision)
        elif args.command == "prepare":
            prepare(args.source, args.branch)
        else:
            return hook(args.name, args.args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Attribution guard: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
