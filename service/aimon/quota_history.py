"""Bounded local log of quota transitions, so upstream jumps are explainable.

One JSON object per line under the ignored logs directory. Each entry keeps
only the instance id, source, measurement time, window ids, used percentage and
reset deadline: no names, credentials, file paths or transcripts. Entries are
written only when a percentage, deadline or window set actually changes; a
repeated check timestamp is not a transition. The file rotates to a single
`.1` backup once it reaches the configured entry bound (or a byte bound), so
it cannot grow without limit. Any failure here is logged and swallowed: quota
collection must never stop because the history file is unwritable.
"""

from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path

from . import log

FILENAME = "quota_history.jsonl"
UNEXPECTED = "drop_before_reset"
MAX_BYTES = 256 * 1024
_MISSING = object()


class QuotaHistory:
    def __init__(self, path: Path, max_entries: int = 400):
        self.path = Path(path)
        self.backup = self.path.with_suffix(self.path.suffix + ".1")
        self.max_entries = max(int(max_entries), 10)
        self._lock = threading.Lock()
        self._last: dict[str, tuple] = {}
        self._lines = 0
        self._size = 0
        self._retry_at = 0.0
        self._load()

    def _load(self) -> None:
        """Restore the last seen value per window so restarts still detect drops."""
        try:
            if not self.path.exists():
                return
            self._size = self.path.stat().st_size
            with self.path.open("r", encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    self._lines += 1
                    try:
                        entry = json.loads(raw)
                        if not isinstance(entry, dict):
                            continue
                        key = _key(entry.get("i"), entry.get("w"))
                    except (ValueError, TypeError):
                        continue
                    if key:
                        self._last[key] = (entry.get("u"), entry.get("r"))
        except OSError as e:
            log.warn("quota_history.load_failed", err=type(e).__name__)

    def observe(self, accounts, now: float | None = None) -> list[dict]:
        """Record changed windows and return the entries written this pass."""
        try:
            return self._observe(accounts, time.time() if now is None else now)
        except Exception as e:  # never let bookkeeping break collection
            log.warn("quota_history.failed", err=type(e).__name__)
            return []

    def _observe(self, accounts, now: float) -> list[dict]:
        changed: list[dict] = []
        with self._lock:
            if time.monotonic() < self._retry_at:
                return []
            before = dict(self._last)
            for account in accounts:
                for window in getattr(account, "windows", ()):
                    key = _key(account.instance_id, window.id)
                    if not key:
                        continue
                    used = _number(window.used_percent)
                    deadline = _number(window.resets_at)
                    previous = self._last.get(key, _MISSING)
                    self._last[key] = (used, deadline)
                    if previous is _MISSING or previous == (used, deadline):
                        continue  # first sight is the baseline, not a transition
                    old_used, old_deadline = previous
                    entry: dict = {
                        "t": int(account.checked_at or now),
                        "i": account.instance_id,
                        "s": account.source,
                        "k": window.kind,
                        "w": window.id,
                        "u": used,
                        "r": deadline,
                    }
                    # A drop while the previous deadline is still ahead cannot be
                    # a refill. Never infer one from the clock alone.
                    if (old_used is not None and used is not None and used < old_used
                            and old_deadline is not None and now < old_deadline):
                        entry["x"] = UNEXPECTED
                    changed.append(entry)
            if changed and not self._append(changed):
                self._last = before  # retry transitions on the next observation
                self._retry_at = time.monotonic() + 60.0
                return []
        return changed

    def _append(self, entries: list[dict]) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self._lines + len(entries) > self.max_entries or self._size > MAX_BYTES:
                self._rotate()
            with self.path.open("a", encoding="utf-8") as fh:
                for entry in entries:
                    line = json.dumps(entry, separators=(",", ":")) + "\n"
                    fh.write(line)
                    self._size += len(line)
                    self._lines += 1
            return True
        except OSError as e:
            log.warn("quota_history.write_failed", err=type(e).__name__)
            return False

    def _rotate(self) -> None:
        try:
            if self.path.exists():
                self.backup.unlink(missing_ok=True)
                self.path.replace(self.backup)
        except OSError as e:
            log.warn("quota_history.rotate_failed", err=type(e).__name__)
            raise
        self._lines = 0
        self._size = 0


def _key(instance_id, window_id) -> str:
    # Identity only: never a display name or a filesystem path.
    if not isinstance(instance_id, str) or not isinstance(window_id, str):
        return ""
    return f"{instance_id}|{window_id}"


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return round(float(value), 2)
