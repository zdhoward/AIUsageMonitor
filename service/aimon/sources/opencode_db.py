"""Free and other-provider activity from OpenCode's SQLite history (opened read-only).

OpenCode 2.x writes `session_message`; older releases wrote `message`. Both are read and
deduplicated by message id.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..models import UsageRecord

V2_SQL = "SELECT id, time_created, data FROM session_message WHERE type = 'assistant' AND time_created >= ?"
V1_SQL = "SELECT id, time_created, data FROM message WHERE time_created >= ?"


def _record(ts_ms: int, data: dict) -> UsageRecord | None:
    if data.get("role", "assistant") != "assistant":
        return None
    model = data.get("model")
    if isinstance(model, dict):  # v2: {"id": ..., "providerID": ...}
        provider, model_id = model.get("providerID"), model.get("id")
    else:  # v1: flat modelID / providerID
        provider, model_id = data.get("providerID"), data.get("modelID")
    tokens = data.get("tokens") or {}
    cache = tokens.get("cache") or {}
    if not provider or not model_id:
        return None
    cost = data.get("cost")
    return UsageRecord(
        ts=ts_ms / 1000.0,
        account=f"opencode:{provider}",
        model=str(model_id),
        uncached_in=int(tokens.get("input") or 0),
        cache_read=int(cache.get("read") or 0),
        cache_write=int(cache.get("write") or 0),
        out=int(tokens.get("output") or 0) + int(tokens.get("reasoning") or 0),
        reported_cost=float(cost) if isinstance(cost, (int, float)) else None,
    )


def read_records(db_path: Path, since: float) -> list[UsageRecord]:
    if not db_path.exists():
        return []
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=2)
    out: dict[str, UsageRecord] = {}
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, sql in (("message", V1_SQL), ("session_message", V2_SQL)):
            if table not in tables:
                continue
            for mid, ts_ms, raw in con.execute(sql, (int(since * 1000),)):
                try:
                    rec = _record(ts_ms, json.loads(raw))
                except (ValueError, TypeError):
                    continue
                if rec:
                    out[mid] = rec
    finally:
        con.close()
    return list(out.values())


def is_free(rec: UsageRecord, extra: list[str]) -> bool:
    provider = rec.account.split(":", 1)[-1]
    model = rec.model.lower()
    return (
        model.endswith("-free")
        or model.endswith(":free")
        or provider in ("nvidia", "litellm", "ollama")
        or provider in extra
    )
