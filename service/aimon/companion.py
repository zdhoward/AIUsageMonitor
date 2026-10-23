"""One loop owns behavior; request threads only enqueue and copy snapshots."""
from __future__ import annotations

import math
import os
import random
import re
import sqlite3
import threading
import time
from pathlib import Path

EXPRESSIONS = ("content", "happy", "curious", "bored", "sleepy", "surprised", "stressed")
REACTIONS = {"pet": ("happy", 4.0, 0.12), "play": ("surprised", 3.0, 0.08),
             "nap": ("sleepy", 8.0, -0.05)}


def allocate_session(path=None, clock=time.time_ns):
    """Commit an ordered uint64 before publishing; SQLite serializes startups.

    Errors deliberately abort construction rather than publishing an unsafe sid.
    TEXT avoids SQLite's signed-int64 limit on the wire's uint64 range.
    """
    if path is None:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
        path = base / "AIUsageMonitor" / "mint-session.sqlite3"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='session'").fetchone()
        if exists:
            rows = db.execute("SELECT sid FROM session").fetchall()
            if len(rows) != 1 or not isinstance(rows[0][0], str) or not re.fullmatch(r"[0-9a-f]{16}", rows[0][0]):
                raise ValueError("corrupt MINT session state; see docs/SETUP.md")
            previous = int(rows[0][0], 16)
        else:
            db.execute("CREATE TABLE session (sid TEXT NOT NULL)")
            previous = 0
        value = max(previous + 1, clock())
        if not 0 < value <= 0xffffffffffffffff:
            raise ValueError("MINT session identity exhausted/out of range")
        sid = f"{value:016x}"
        db.execute("DELETE FROM session")
        db.execute("INSERT INTO session VALUES (?)", (sid,))
        db.execute("COMMIT")
        return sid
    finally:
        db.close()  # rolls back any failed allocation


class LocalMetrics:
    """Windows kernel counters only; unsupported/error samples are unavailable."""
    def __init__(self):
        self.previous = None

    def sample(self):
        try:
            import ctypes as c
            from ctypes import wintypes as w

            class Memory(c.Structure):
                _fields_ = [("length", w.DWORD), ("load", w.DWORD)] + [
                    (name, c.c_ulonglong) for name in
                    ("total", "avail", "page", "avail_page", "virtual", "avail_virtual", "extended")]

            idle, kernel, user = w.FILETIME(), w.FILETIME(), w.FILETIME()
            api = c.windll.kernel32
            if not api.GetSystemTimes(c.byref(idle), c.byref(kernel), c.byref(user)):
                raise OSError("GetSystemTimes")
            value = lambda t: (t.dwHighDateTime << 32) | t.dwLowDateTime
            current = (value(idle), value(kernel) + value(user))
            cpu = None
            if self.previous and current[1] > self.previous[1]:
                cpu = 100 * (1 - (current[0] - self.previous[0]) / (current[1] - self.previous[1]))
            self.previous = current
            mem = Memory()
            mem.length = c.sizeof(mem)
            ram = float(mem.load) if api.GlobalMemoryStatusEx(c.byref(mem)) else None
            return cpu, ram
        except (AttributeError, OSError, ValueError):
            self.previous = None
            return None, None


class Companion:
    def __init__(self, now=None, rng=None, session_allocator=None):
        now = time.monotonic() if now is None else now
        self.lock = threading.Lock()
        self.sid = (session_allocator or allocate_session)()
        self.rng = rng or random.Random()
        self.mood = 0.5
        self.mood_target = 0.5
        self.last = now
        self.idle_until = now
        self.idle = "content"
        self.pending = None
        self.active = None
        self.until = now
        self.stress = [False, False]
        self.sample_at = float("-inf")
        self.revision = 0
        self.published = None
        self.lease_until = now

    def request(self, action):
        if action not in REACTIONS:
            return 400
        with self.lock:
            if self.pending == action or self.active == action:
                return 200
            if self.pending or self.active:
                return 429
            self.pending = action
            return 202

    def tick(self, now, metrics=None):
        with self.lock:
            started = self.pending is not None
            dt = max(0.0, now - self.last)
            self.last = now
            # Gentle return to baseline; stress never writes mood.
            self.mood += (self.mood_target - self.mood) * (1 - math.exp(-dt / 20))
            self.mood_target = 0.5 + (self.mood_target - 0.5) * math.exp(-dt / 300)
            if metrics is not None:
                self.sample_at = now
                for i, value in enumerate(metrics):
                    if value is None or not math.isfinite(value) or not 0 <= value <= 100:
                        self.stress[i] = False
                    elif value >= 80:
                        self.stress[i] = True
                    elif value < 75:
                        self.stress[i] = False
            if now - self.sample_at > 5:
                self.stress = [False, False]
            if self.active and now >= self.until:
                self.active = None
            if self.pending:
                self.active, self.pending = self.pending, None
                _, duration, delta = REACTIONS[self.active]
                self.until = now + duration
                self.mood_target = min(1.0, max(0.0, self.mood_target + delta))
            if now >= self.idle_until:
                self.idle = self.rng.choices(
                    ("content", "happy", "curious", "bored", "sleepy"),
                    (5, 1 + 3 * self.mood, 2, 2 - self.mood, 1))[0]
                self.idle_until = now + self.rng.uniform(12, 25)
            expression = (REACTIONS[self.active][0] if self.active else
                          "stressed" if any(self.stress) else self.idle)
            self.revision += 1
            self.published = {"sid": self.sid, "n": self.revision, "e": expression}
            self.lease_until = min(now + 15, self.until) if self.active else now + 15
            return started

    def snapshot(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            if self.published is None or now >= self.lease_until:
                return None
            return {**self.published, "ttl": max(1, int((self.lease_until - now) * 1000))}
