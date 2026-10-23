"""Deferred to owner-declared sprint end; no providers or serial hardware."""
import json
import random
import time
import unittest
import tempfile
import sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from aimon.companion import Companion, allocate_session
from aimon.config import Settings
from aimon.server import App
from aimon.snapshot import State, build_payload
from aimon.pricing import Pricing
from aimon.models import Account, Window


class CompanionTests(unittest.TestCase):
    def setUp(self):
        # App() too must never allocate from the real user's durable state.
        allocator = patch("aimon.companion.allocate_session", return_value="0000000000000001")
        allocator.start()
        self.addCleanup(allocator.stop)

    def make(self):
        return Companion(now=0, rng=random.Random(9))

    def test_reaction_coalesces_without_extension(self):
        c = self.make()
        self.assertEqual(c.request("pet"), 202)
        self.assertEqual(c.request("pet"), 200)
        self.assertEqual(c.request("play"), 429)
        c.tick(0)
        self.assertEqual(c.snapshot(0)["e"], "happy")
        self.assertEqual(c.request("pet"), 200)
        c.tick(3)
        self.assertEqual(c.until, 4)
        self.assertLessEqual(c.snapshot(3)["ttl"], 1000)
        self.assertIsNone(c.snapshot(4))  # stalled owner never replays reaction
        c.tick(4)
        self.assertIsNone(c.active)
        self.assertEqual(c.request("bad"), 400)

    def test_independent_hysteresis_and_missing(self):
        c = self.make()
        c.tick(0, (80, 0))
        self.assertEqual(c.snapshot(0)["e"], "stressed")
        c.tick(1, (75, 80))
        self.assertEqual(c.stress, [True, True])
        c.tick(2, (74.9, 76))
        self.assertEqual(c.stress, [False, True])
        c.tick(3, (None, None))
        self.assertEqual(c.stress, [False, False])
        c.tick(4, (90, 90))
        c.tick(10)
        self.assertEqual(c.stress, [False, False])

    def test_reaction_overrides_then_stress_returns_without_mood_damage(self):
        c = self.make()
        c.tick(0, (90, 0))
        self.assertEqual(c.mood, 0.5)
        c.request("play")
        c.tick(1, (90, 0))
        self.assertEqual(c.snapshot(1)["e"], "surprised")
        c.tick(4, (90, 0))
        self.assertEqual(c.snapshot(4)["e"], "stressed")
        self.assertTrue(0 <= c.mood <= 1)

    def test_snapshot_is_copy_and_reads_do_not_evolve(self):
        c = self.make()
        c.tick(0)
        original = c.snapshot(0)
        changed = c.snapshot(0)
        changed["e"] = "bad"
        self.assertEqual(c.snapshot(0), original)
        self.assertEqual(c.revision, 1)
        self.assertIsNone(c.snapshot(16))

    def test_wire_budget_and_overflow_fallback(self):
        c = self.make()
        c.tick(0)
        p = build_payload(State(), 1792600000, Pricing({}), Settings())
        p["mint"] = c.snapshot(0)
        self.assertLessEqual(len(json.dumps(p, separators=(",", ":")).encode()), 4095)
        # App's actual overflow path must remain valid JSON and carry no quota
        # measurements that might falsely refresh the firmware cache.
        from unittest.mock import patch
        app = App(Settings(serial_enabled=False))
        with patch("aimon.server.build_payload", return_value={"acc": "x" * 5000}):
            p = app.device_payload()
        self.assertNotIn("acc", p)
        self.assertLessEqual(len(json.dumps(p).encode()), 4095)

    def test_companion_push_does_not_renew_measurement(self):
        from unittest.mock import patch
        app = App(Settings(serial_enabled=False, limits_stale_s=60))
        app.collector.state = State(accounts=[Account(
            "codex", "Codex", "codex", None, None,
            [Window("primary", "session", "5h", 80, 2000)], checked_at=1000)])
        app.companion.request("pet")
        app.companion.tick(time.monotonic())
        with patch("aimon.server.time.time", return_value=1100):
            first = app.device_payload()
        with patch("aimon.server.time.time", return_value=1110):
            second = app.device_payload()
        self.assertEqual(first["acc"][0]["age"], 100)
        self.assertEqual(first["mint"]["e"], "happy")
        self.assertEqual(second["acc"][0]["age"], 110)
        self.assertEqual(second["acc"][0]["st"], 1)
        self.assertEqual(second["acc"][0]["w"][0]["r"], 890)


class SessionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "session.sqlite3"

    def test_restart_with_clock_rollback(self):
        first = allocate_session(self.path, lambda: 1000)
        second = allocate_session(self.path, lambda: 10)
        self.assertEqual((first, second), ("00000000000003e8", "00000000000003e9"))

    def test_concurrent_allocations_are_unique_and_persisted(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(lambda _: allocate_session(self.path, lambda: 1), range(24)))
        self.assertEqual(sorted(ids), [f"{i:016x}" for i in range(1, 25)])
        self.assertEqual(allocate_session(self.path, lambda: 0), f"{25:016x}")

    def test_corruption_exhaustion_and_failed_allocation_stop_publication(self):
        allocate_session(self.path, lambda: 1)
        for stored in ("broken", "ffffffffffffffff"):
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE session SET sid=?", (stored,))
            db.close()
            with self.assertRaises(ValueError):
                Companion(session_allocator=lambda: allocate_session(self.path, lambda: 1))
        with self.assertRaises(ValueError):
            allocate_session(Path(self.path.parent) / "range.sqlite3", lambda: 1 << 64)
        self.path.write_bytes(b"not a database")
        with self.assertRaises(sqlite3.DatabaseError):
            allocate_session(self.path, lambda: 1)


if __name__ == "__main__":
    unittest.main()
