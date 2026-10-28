"""Token usage from Claude Code transcripts and Codex rollout logs.

Files are read incrementally: each refresh reads only bytes appended since the last
pass, and only complete lines. Files untouched for longer than the history window
are skipped.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .. import log
from ..models import UsageRecord, Window
from .t3_limits import parse_iso, window_label


@dataclass
class _FileState:
    offset: int = 0
    records: dict[str, UsageRecord] = field(default_factory=dict)
    # Codex per-file parse state
    model: str = "unknown"
    last_total: tuple | None = None
    rate_limits: tuple[float, dict] | None = None  # (ts, payload)


def parse_claude_line(obj: dict, account: str) -> tuple[str, UsageRecord] | None:
    if obj.get("type") != "assistant":
        return None
    msg = obj.get("message") or {}
    usage = msg.get("usage")
    model = msg.get("model") or "unknown"
    if not isinstance(usage, dict) or model == "<synthetic>":
        return None
    ts = parse_iso(obj.get("timestamp"))
    if ts is None:
        return None
    key = f"{msg.get('id')}:{obj.get('requestId')}"
    rec = UsageRecord(
        ts=ts,
        account=account,
        model=model,
        uncached_in=int(usage.get("input_tokens") or 0),
        cache_read=int(usage.get("cache_read_input_tokens") or 0),
        cache_write=int(usage.get("cache_creation_input_tokens") or 0),
        out=int(usage.get("output_tokens") or 0),
    )
    return key, rec


def parse_codex_line(obj: dict, account: str, st: _FileState, line_no: int) -> tuple[str, UsageRecord] | None:
    kind = obj.get("type")
    payload = obj.get("payload") or {}
    if kind == "turn_context":
        st.model = payload.get("model") or st.model
        return None
    if kind != "event_msg" or payload.get("type") != "token_count":
        return None
    ts = parse_iso(obj.get("timestamp"))
    if ts is None:
        return None
    if isinstance(payload.get("rate_limits"), dict):
        st.rate_limits = (ts, payload["rate_limits"])
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    total = info.get("total_token_usage") or {}
    total_key = tuple(sorted(total.items()))
    if total_key == st.last_total:
        return None  # repeated event (e.g. a rate-limit update) without new tokens
    st.last_total = total_key
    last = info.get("last_token_usage") or {}
    inp = int(last.get("input_tokens") or 0)
    cached = int(last.get("cached_input_tokens") or 0)
    rec = UsageRecord(
        ts=ts,
        account=account,
        model=st.model,
        uncached_in=max(inp - cached, 0),
        cache_read=cached,
        cache_write=int(last.get("cache_write_input_tokens") or 0),
        out=int(last.get("output_tokens") or 0),
    )
    return f"L{line_no}", rec


def codex_windows(rate_limits: dict) -> list[Window]:
    out = []
    for wid, kind in (("primary", "session"), ("secondary", "weekly")):
        w = rate_limits.get(wid)
        if not isinstance(w, dict):
            continue
        mins = w.get("window_minutes")
        used = w.get("used_percent")
        out.append(
            Window(
                id=wid,
                kind=kind,
                label=window_label(kind, int(mins) if mins else None, wid),
                used_percent=float(used) if isinstance(used, (int, float)) else None,
                resets_at=float(w["resets_at"]) if isinstance(w.get("resets_at"), (int, float)) else None,
                window_mins=int(mins) if mins else None,
            )
        )
    return out


class SessionLogScanner:
    """Keeps parsed records for one transcript root (one account)."""

    def __init__(self, root: Path, account: str, flavor: str, history_days: int,
                 discovery_s: float = 30.0):
        self.root = root
        self.account = account
        self.flavor = flavor  # "claude" | "codex"
        self.history_s = history_days * 86400
        self.discovery_s = max(float(discovery_s), 0.0)
        self._files: dict[str, _FileState] = {}
        self._dirs: list[str] | None = None  # None: first pass walks immediately
        self._dirs_at = 0.0

    def _discover(self, now: float) -> list[str]:
        """Reuse the directory listing for a bounded interval.

        A cached directory that has since disappeared fails to list and simply
        contributes no files, so removals are handled on the next pass.
        """
        if self._dirs is not None and now - self._dirs_at < self.discovery_s:
            return self._dirs
        dirs: list[str] = []
        try:
            for dirpath, _dirs, _names in os.walk(self.root):
                dirs.append(dirpath)
        except OSError as e:  # an unreadable root just yields nothing
            log.warn("session_logs.discovery_failed", account=self.account, err=type(e).__name__)
        self._dirs, self._dirs_at = dirs, now
        return dirs

    def refresh(self, now: float | None = None) -> None:
        now = now or time.time()
        cutoff = now - self.history_s
        seen = set()
        if not self.root.exists():
            # The root is gone: drop cached records and rediscover on return.
            self._files.clear()
            self._dirs = None
            return
        for dirpath in self._discover(now):
            try:
                entries = list(os.scandir(dirpath))
            except OSError:  # removed since discovery; its files drop out below
                continue
            for entry in entries:
                if not entry.name.endswith(".jsonl"):
                    continue
                try:
                    if not entry.is_file():
                        continue
                    st = entry.stat()
                except OSError:
                    continue
                if st.st_mtime < cutoff:
                    continue
                seen.add(entry.path)
                self._read_file(entry.path, st.st_size)
        for gone in set(self._files) - seen:
            del self._files[gone]
        for fs in self._files.values():
            for k in [k for k, r in fs.records.items() if r.ts < cutoff]:
                del fs.records[k]

    def _read_file(self, path: str, size: int) -> None:
        fs = self._files.get(path)
        if fs is None or size < fs.offset:
            fs = self._files[path] = _FileState()
        if size == fs.offset:
            return
        try:
            with open(path, "rb") as fh:
                fh.seek(fs.offset)
                chunk = fh.read(size - fs.offset)
        except OSError as e:
            log.warn("session_logs.read_failed", file=os.path.basename(path), err=type(e).__name__)
            return
        end = chunk.rfind(b"\n")
        if end < 0:
            return  # no complete line yet
        line_no = fs.offset  # byte offset makes a stable per-file key
        for raw in chunk[: end + 1].split(b"\n"):
            pos = line_no
            line_no += len(raw) + 1
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            if self.flavor == "claude":
                parsed = parse_claude_line(obj, self.account)
            else:
                parsed = parse_codex_line(obj, self.account, fs, pos)
            if parsed:
                key, rec = parsed
                fs.records[key] = rec
        fs.offset += end + 1

    def records(self) -> dict[str, UsageRecord]:
        merged: dict[str, UsageRecord] = {}
        for path, fs in self._files.items():
            for k, r in fs.records.items():
                # Claude keys are global message ids (dedupes resumed sessions);
                # Codex keys are per-file offsets, so prefix them with the path.
                merged[k if self.flavor == "claude" else f"{path}:{k}"] = r
        return merged

    def latest_rate_limits(self) -> tuple[float, dict] | None:
        found = [fs.rate_limits for fs in self._files.values() if fs.rate_limits]
        return max(found, key=lambda x: x[0]) if found else None
