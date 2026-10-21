"""Current request status from T3's orchestration state (statev2.sqlite, opened read-only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..models import Activity
from .t3_limits import parse_iso

RUNS_SQL = """
SELECT r.provider_instance_id, r.status, r.requested_at, r.completed_at,
       (SELECT s.model FROM orchestration_v2_projection_provider_sessions s
         WHERE s.thread_id = r.thread_id
           AND s.provider_instance_id = r.provider_instance_id
         ORDER BY s.updated_at DESC LIMIT 1) AS model
FROM orchestration_v2_projection_runs r
WHERE r.status = 'running' OR r.completed_at IS NOT NULL
ORDER BY COALESCE(r.completed_at, r.requested_at) DESC
LIMIT 50
"""


def read_activity(db_path: Path, now: float, max_run_age_s: float) -> Activity:
    if not db_path.exists():
        return Activity(state="unknown")
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=2)
    try:
        rows = con.execute(RUNS_SQL).fetchall()
    finally:
        con.close()
    return activity_from_rows(rows, now, max_run_age_s)


def activity_from_rows(rows, now: float, max_run_age_s: float) -> Activity:
    running = []
    last_done = None
    for instance, status, requested, completed, model in rows:
        started = parse_iso(requested)
        if status == "running":
            if started and now - started <= max_run_age_s:
                running.append((started, instance, model))
        elif last_done is None:
            last_done = (parse_iso(completed), instance, model)
    if running:
        started, instance, model = max(running)
        return Activity("running", instance, model, len(running), started)
    if last_done:
        done, instance, model = last_done
        return Activity("idle", instance, model, 0, done)
    return Activity(state="idle")
