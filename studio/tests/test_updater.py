"""Updater tests against scratch git repos (no network, no real checkout touched)."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from studio import updater

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def run(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout.strip()


def commit(cwd: Path, name: str, text: str, msg: str) -> None:
    (cwd / name).write_text(text, encoding="utf-8")
    run(cwd, "add", name)
    run(cwd, "commit", "-m", msg)


class UpdaterCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.work = base / "upstream-work"
        self.work.mkdir()
        run(self.work, "init", "-b", "main")
        commit(self.work, "app.txt", "one\n", "first")
        commit(self.work, "other.txt", "x\n", "second")
        run(self.work, "tag", "v1.0.0")
        self.root = base / "user"
        run(base, "clone", str(self.work), "user")
        run(self.root, "switch", "-c", "my-setup")
        # the user's own change, in a tracked file
        commit(self.root, "mine.txt", "mine\n", "my profile")

    def tearDown(self):
        self._tmp.cleanup()

    def upstream_commit(self, name, text, msg):
        commit(self.work, name, text, msg)

    def test_up_to_date(self):
        s = updater.status(self.root, check=True)
        self.assertEqual(s["behind"], 0)
        self.assertEqual(s["branch"], "my-setup")
        self.assertEqual(s["blocker"], "")
        self.assertTrue(s["checked"])

    def test_pending_and_clean_merge_preview(self):
        self.upstream_commit("new.txt", "n\n", "add feature")
        s = updater.status(self.root, check=True)
        self.assertEqual(s["behind"], 1)
        self.assertIn("add feature", s["pending"][0])
        self.assertEqual(s["conflicts"], [])

    def test_apply_clean_merge_keeps_my_work_and_tags_backup(self):
        self.upstream_commit("new.txt", "n\n", "add feature")
        res = updater.apply(self.root, lambda _l: None)
        self.assertTrue(res["ok"], res)
        self.assertTrue((self.root / "new.txt").is_file())
        self.assertTrue((self.root / "mine.txt").is_file())
        self.assertIn(res["backup"], updater.backups(self.root))
        # local main moved with upstream
        self.assertEqual(run(self.root, "rev-parse", "main"), run(self.root, "rev-parse", "origin/main"))
        self.assertEqual(updater.status(self.root)["behind"], 0)

    def test_conflict_is_previewed_then_aborted_cleanly(self):
        commit(self.root, "app.txt", "mine\n", "edit shared file")
        self.upstream_commit("app.txt", "theirs\n", "upstream edit")
        s = updater.status(self.root, check=True)
        self.assertEqual(s["conflicts"], ["app.txt"])
        before = run(self.root, "rev-parse", "HEAD")
        res = updater.apply(self.root, lambda _l: None)
        self.assertFalse(res["ok"])
        self.assertEqual(res["conflicts"], ["app.txt"])
        self.assertEqual(run(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(run(self.root, "status", "--porcelain"), "")  # no half-merged tree
        self.assertEqual((self.root / "app.txt").read_text(encoding="utf-8"), "mine\n")
        self.assertIn("app.txt", updater.agent_prompt(res["conflicts"]))

    def test_dirty_tree_blocks_unless_saved_first(self):
        self.upstream_commit("new.txt", "n\n", "add feature")
        (self.root / "mine.txt").write_text("edited\n", encoding="utf-8")
        res = updater.apply(self.root, lambda _l: None)
        self.assertFalse(res["ok"])
        self.assertIn("uncommitted", res["error"])
        res = updater.apply(self.root, lambda _l: None, commit_first=True)
        self.assertTrue(res["ok"], res)
        self.assertEqual((self.root / "mine.txt").read_text(encoding="utf-8"), "edited\n")

    def test_local_main_with_own_commits_is_blocked(self):
        run(self.root, "switch", "main")
        commit(self.root, "stray.txt", "s\n", "oops on main")
        run(self.root, "switch", "my-setup")
        s = updater.status(self.root, check=True)
        self.assertIn("main", s["blocker"])
        self.assertFalse(updater.apply(self.root, lambda _l: None)["ok"])

    def test_update_on_main_fast_forwards(self):
        run(self.root, "switch", "main")
        self.upstream_commit("new.txt", "n\n", "add feature")
        res = updater.apply(self.root, lambda _l: None)
        self.assertTrue(res["ok"], res)
        self.assertTrue((self.root / "new.txt").is_file())

    def test_rollback_restores_pre_update_state(self):
        before = run(self.root, "rev-parse", "HEAD")
        self.upstream_commit("new.txt", "n\n", "add feature")
        self.assertTrue(updater.apply(self.root, lambda _l: None)["ok"])
        self.assertNotEqual(run(self.root, "rev-parse", "HEAD"), before)
        res = updater.rollback(self.root)
        self.assertTrue(res["ok"], res)
        self.assertEqual(run(self.root, "rev-parse", "HEAD"), before)

    def test_rollback_without_backup(self):
        self.assertFalse(updater.rollback(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
