"""Run: cd service && python -m unittest -v"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from aimon.config import Settings
from aimon.models import Account, Activity, UsageRecord, Window
from aimon.pricing import Pricing
from aimon.snapshot import State, build_payload, select_accounts, short_model
from aimon.sources import antigravity, opencode_db, openrouter, t3_activity, t3_limits
from aimon.sources.session_logs import SessionLogScanner

NOW = 1_792_600_000.0  # fixed clock
PRICING = Pricing({"m-priced": {"input_cost_per_token": 1e-6, "output_cost_per_token": 1e-5, "cache_read_input_token_cost": 1e-7}})


def iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(ts))


class T3LimitsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "caches").mkdir()
        (self.home / "userdata").mkdir()
        (self.home / "userdata" / "settings.json").write_text(
            json.dumps({"providerInstances": {"claudeAgent": {"displayName": "CL1"}}}), encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, doc):
        (self.home / "caches" / name).write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")

    def test_reads_windows_and_hides_email(self):
        self.write(
            "claudeAgent.json",
            {
                "driver": "claudeAgent",
                "instanceId": "claudeAgent",
                "enabled": True,
                "accentColor": "#eb4325",
                "auth": {"status": "authenticated", "email": "secret@example.com", "label": "Claude Pro Subscription"},
                "usageLimits": {
                    "checkedAt": iso(NOW - 60),
                    "windows": [
                        {"id": "five_hour", "kind": "session", "windowDurationMins": 300, "usedPercent": 37, "resetsAt": iso(NOW + 3600)},
                        {"id": "seven_day", "kind": "weekly", "windowDurationMins": 10080, "usedPercent": 91, "resetsAt": iso(NOW + 86400)},
                    ],
                },
            },
        )
        [acct] = t3_limits.read_accounts(self.home)
        self.assertEqual(acct.name, "CL1")
        self.assertEqual(acct.plan, "Pro")
        self.assertEqual(acct.color, "eb4325")
        self.assertEqual([w.label for w in acct.windows], ["5h", "7d"])
        self.assertEqual(acct.windows[1].used_percent, 91)
        self.assertNotIn("secret", json.dumps(acct.__dict__, default=str))

    def test_reset_credits(self):
        base = {"driver": "claudeAgent", "enabled": True, "usageLimits": {"checkedAt": iso(NOW), "windows": []}}
        self.write("a.json", {**base, "instanceId": "a", "usageLimits": {**base["usageLimits"], "resetCredits": {"availableCount": 2}}})
        self.write("b.json", {**base, "instanceId": "b"})
        by_id = {a.instance_id: a for a in t3_limits.read_accounts(self.home)}
        self.assertEqual(by_id["a"].reset_credits, 2)
        self.assertIsNone(by_id["b"].reset_credits)

    def test_malformed_and_irrelevant_caches_are_skipped(self):
        self.write("broken.json", "{not json")
        self.write("grok.json", {"driver": "grok", "enabled": True})
        self.assertEqual(t3_limits.read_accounts(self.home), [])

    def test_missing_limits_is_unavailable_not_zero(self):
        self.write("codex.json", {"driver": "codex", "enabled": True, "auth": {"status": "unauthenticated"}})
        [acct] = t3_limits.read_accounts(self.home)
        self.assertEqual(acct.windows, [])
        self.assertEqual(acct.unavailable, "signed out")

    def test_unsupported_reason_is_kept(self):
        self.write("codex.json", {"driver": "codex", "enabled": True, "usageLimits": {"checkedAt": iso(NOW), "windows": [], "unavailable": {"reason": "unsupported"}}})
        [acct] = t3_limits.read_accounts(self.home)
        self.assertEqual(acct.unavailable, "unsupported")


class AntigravityTests(unittest.TestCase):
    """Retained fixtures for the direct Gemini quota reader (not executed in this lane)."""

    def models(self):
        return {
            "gemini-2.5-pro": {
                "modelProvider": "MODEL_PROVIDER_GOOGLE",
                "quotaInfo": {"remainingFraction": 0.75, "resetTime": iso(NOW + 3600)},
                "weeklyQuotaInfo": {"remainingFraction": 0.5, "resetTime": iso(NOW + 86400)},
            },
            "gemini-3-flash": {
                "modelProvider": "MODEL_PROVIDER_GOOGLE",
                "quotaInfo": {"remainingFraction": 0.9, "resetTime": iso(NOW + 7200)},
            },
            "claude-opus-5-5-high": {
                "modelProvider": "MODEL_PROVIDER_ANTHROPIC",
                "quotaInfo": {"remainingFraction": 0.0, "resetTime": iso(NOW + 3600)},
            },
        }

    def test_fraction_is_remaining_and_aggregates_gemini_only(self):
        self.assertAlmostEqual(antigravity.fraction_to_used(0.92816395), 7.183605, places=4)
        self.assertEqual(antigravity.fraction_to_used(1), 0)
        self.assertEqual(antigravity.fraction_to_used(0), 100)
        self.assertEqual(antigravity.fraction_to_used(-0.5), 100)  # clamped, never negative
        self.assertEqual(antigravity.fraction_to_used(1.5), 0)
        for bad in (None, True, "0.5", float("nan")):
            self.assertIsNone(antigravity.fraction_to_used(bad))

        antigrav, argon = antigravity.accounts_from_models(self.models(), NOW)
        self.assertEqual(antigrav.name, "Antigrav")
        self.assertEqual([(w.label, round(w.used_percent, 1)) for w in antigrav.windows],
                         [("5h", 25.0), ("7d", 50.0)])
        self.assertEqual(antigrav.checked_at, NOW)
        # Claude's exhausted model must never become the Gemini number.
        self.assertNotIn(100.0, [w.used_percent for w in antigrav.windows])

    def test_argon_quota_does_not_replace_gemini_allowance(self):
        models = self.models()
        models[antigravity.ARGON_MODEL] = {
            "modelProvider": "MODEL_PROVIDER_GOOGLE",
            "quotaInfo": {"remainingFraction": 0.0, "resetTime": iso(NOW + 3600)},
        }
        antigrav, argon = antigravity.accounts_from_models(models, NOW)
        self.assertEqual(antigrav.windows[0].used_percent, 25.0)
        self.assertEqual(argon.windows[0].used_percent, 100.0)

    def test_missing_argon_is_distinct_and_unknown(self):
        antigrav, argon = antigravity.accounts_from_models(self.models(), NOW)
        self.assertEqual(argon.name, "Argon")
        self.assertEqual(argon.windows, [])
        self.assertIsNone(argon.checked_at)
        self.assertEqual(argon.unavailable, antigravity.ARGON_UNAVAILABLE)
        self.assertGreaterEqual(len(antigrav.windows), 1)

    def test_optional_weekly_is_never_invented(self):
        doc = {"gemini-3-flash": self.models()["gemini-3-flash"]}
        antigrav, _argon = antigravity.accounts_from_models(doc, NOW)
        self.assertEqual([w.label for w in antigrav.windows], ["5h"])
        self.assertIsNotNone(antigrav.windows[0].resets_at)

    def test_malformed_data_is_bounded_and_unavailable(self):
        with self.assertRaises(antigravity.QuotaError):
            antigravity.accounts_from_models(["not", "a", "map"], NOW)
        antigrav, argon = antigravity.accounts_from_models(
            {"gemini-3-flash": "junk", "gemini-2.5-pro": {"quotaInfo": {"remainingFraction": "x"}}}, NOW
        )
        self.assertEqual(antigrav.windows, [])
        self.assertEqual(antigrav.unavailable, "no Gemini quota")
        self.assertEqual(argon.unavailable, antigravity.ARGON_UNAVAILABLE)

    def test_failed_refresh_retains_last_good_checked_at(self):
        with tempfile.TemporaryDirectory() as d:
            reader = antigravity.AntigravityReader(Path(d), refresh_s=300, timeout_s=1)
            good = antigravity.accounts_from_models(self.models(), NOW - 600)
            reader._good = good
            reader._next = 0.0
            with mock.patch.object(antigravity, "discover_token",
                                   return_value=antigravity.TokenChoice(None, None, "no stored login")):
                accounts = reader.read(NOW)
            antigrav = next(a for a in accounts if a.name == "Antigrav")
            self.assertEqual(antigrav.checked_at, NOW - 600)  # original, not refreshed
            self.assertEqual([w.label for w in antigrav.windows], ["5h", "7d"])
            self.assertEqual(reader._next, NOW + 300)  # failure also waits the cadence

    def test_success_is_cached_for_the_cadence(self):
        with tempfile.TemporaryDirectory() as d:
            reader = antigravity.AntigravityReader(Path(d), refresh_s=300, timeout_s=1)
            reader._good = antigravity.accounts_from_models(self.models(), NOW)
            reader._next = NOW + 300
            with mock.patch.object(antigravity, "_post_json", side_effect=AssertionError("must not poll")):
                accounts = reader.read(NOW + 10)
            self.assertEqual(next(a for a in accounts if a.name == "Antigrav").checked_at, NOW)


class AccountSelectionTests(unittest.TestCase):
    def test_cap_keeps_pinned_providers_over_duplicate_caches(self):
        def acct(iid, name, driver):
            return Account(iid, name, driver, None, "888888")

        accounts = [
            acct("claudeAgent", "A", "claudeAgent"),
            acct("claudeAgent_claude_2", "B", "claudeAgent"),
            acct("codex", "Codex", "codex"),
            acct("codex_dup", "Codex 2", "codex"),
            acct("antigravity_direct", "Antigrav", "antigravity"),
            acct("antigravity_argon", "Argon", "antigravity"),
            acct("cursor", "Cursor", "cursor"),
        ]
        kept = [a.name for a in select_accounts(accounts)]
        self.assertLessEqual(len(kept), 6)
        self.assertEqual(set(kept), {"A", "B", "Codex", "Codex 2", "Antigrav", "Argon"})


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_claude_dedupes_message_blocks_and_reads_appends_incrementally(self):
        f = self.root / "p" / "s.jsonl"
        f.parent.mkdir()
        line = lambda mid, out: json.dumps(
            {"type": "assistant", "timestamp": iso(time.time()), "requestId": "r" + mid,
             "message": {"id": mid, "model": "m-priced", "usage": {"input_tokens": 5, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 10, "output_tokens": out}}}
        ) + "\n"
        f.write_text(line("a", 1) + line("a", 7) + json.dumps({"type": "user"}) + "\n", encoding="utf-8")
        sc = SessionLogScanner(self.root, "claudeAgent", "claude", 7)
        sc.refresh()
        recs = list(sc.records().values())
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].out, 7)
        with f.open("a", encoding="utf-8") as fh:
            fh.write(line("b", 3))
            fh.write('{"type": "assistant", "partial')  # incomplete line must wait
        sc.refresh()
        self.assertEqual(len(sc.records()), 2)

    def test_codex_token_counts_model_and_rate_limits(self):
        f = self.root / "rollout.jsonl"
        tc = lambda total, last, rl=None: json.dumps(
            {"timestamp": iso(time.time()), "type": "event_msg",
             "payload": {"type": "token_count", "info": {"total_token_usage": {"t": total}, "last_token_usage": last}, **({"rate_limits": rl} if rl else {})}}
        ) + "\n"
        rl = {"primary": {"used_percent": 12.0, "window_minutes": 300, "resets_at": NOW + 100}, "secondary": {"used_percent": 4.0, "window_minutes": 10080, "resets_at": NOW + 9000}}
        f.write_text(
            json.dumps({"timestamp": iso(time.time()), "type": "turn_context", "payload": {"model": "gpt-x"}}) + "\n"
            + tc(10, {"input_tokens": 100, "cached_input_tokens": 60, "output_tokens": 9}, rl)
            + tc(10, {"input_tokens": 100, "cached_input_tokens": 60, "output_tokens": 9}),  # repeat, no new tokens
            encoding="utf-8",
        )
        sc = SessionLogScanner(self.root, "codex", "codex", 7)
        sc.refresh()
        [rec] = sc.records().values()
        self.assertEqual((rec.model, rec.uncached_in, rec.cache_read, rec.out), ("gpt-x", 40, 60, 9))
        ts, payload = sc.latest_rate_limits()
        self.assertEqual(payload["primary"]["used_percent"], 12.0)

    def test_truncated_file_is_rescanned(self):
        f = self.root / "s.jsonl"
        rec = json.dumps({"type": "assistant", "timestamp": iso(time.time()), "requestId": "r", "message": {"id": "x", "model": "m", "usage": {"output_tokens": 1}}}) + "\n"
        f.write_text(rec * 3, encoding="utf-8")
        sc = SessionLogScanner(self.root, "a", "claude", 7)
        sc.refresh()
        f.write_text("", encoding="utf-8")
        sc.refresh()
        self.assertEqual(len(sc.records()), 0)


class ActivityTests(unittest.TestCase):
    def test_running_beats_idle_and_old_runs_are_ignored(self):
        rows = [
            ("claudeAgent_claude_2", "running", iso(NOW - 30), None, "claude-opus-5-5"),
            ("codex", "running", iso(NOW - 10 * 3600), None, "gpt"),  # stuck, ignored
            ("claudeAgent", "completed", iso(NOW - 600), iso(NOW - 500), "claude-sonnet-5-5"),
        ]
        a = t3_activity.activity_from_rows(rows, NOW, 6 * 3600)
        self.assertEqual((a.state, a.instance_id, a.running), ("running", "claudeAgent_claude_2", 1))

    def test_idle_reports_last_completed(self):
        rows = [("claudeAgent", "completed", iso(NOW - 600), iso(NOW - 500), "m")]
        a = t3_activity.activity_from_rows(rows, NOW, 3600)
        self.assertEqual((a.state, a.instance_id), ("idle", "claudeAgent"))
        self.assertAlmostEqual(a.since, NOW - 500, delta=1)


class OpenCodeTests(unittest.TestCase):
    def test_reads_v1_and_v2_tables(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "oc.db"
            con = sqlite3.connect(db)
            con.execute("create table message (id text, time_created int, data text)")
            con.execute("create table session_message (id text, type text, time_created int, data text)")
            ms = int(NOW * 1000)
            con.execute("insert into message values ('m1', ?, ?)", (ms, json.dumps({"role": "assistant", "providerID": "nvidia", "modelID": "z-ai/glm", "tokens": {"input": 5, "output": 2, "cache": {}}, "cost": 0})))
            con.execute("insert into session_message values ('m2','assistant', ?, ?)", (ms, json.dumps({"model": {"id": "deepseek-free", "providerID": "opencode"}, "tokens": {"input": 1, "output": 1, "reasoning": 1, "cache": {"read": 3}}, "cost": 0})))
            con.commit()
            con.close()
            recs = opencode_db.read_records(db, NOW - 10)
        self.assertEqual(sorted(r.account for r in recs), ["opencode:nvidia", "opencode:opencode"])
        self.assertTrue(all(opencode_db.is_free(r, []) for r in recs))

    def test_missing_db_is_empty(self):
        self.assertEqual(opencode_db.read_records(Path("Z:/nope/oc.db"), 0), [])


class OpenRouterTests(unittest.TestCase):
    def test_parse(self):
        st = openrouter.parse({"free_model_daily_requests": {"used": 3, "limit": 50}, "usage_daily": 0.25, "effective_budget": {"remaining_usd": 0.75}, "is_free_tier": True}, NOW)
        self.assertEqual((st.free_used, st.free_limit, st.usd_daily, st.budget_remaining), (3, 50, 0.25, 0.75))


class PayloadTests(unittest.TestCase):
    def settings(self):
        return Settings()

    def state(self, **kw):
        acct = Account("claudeAgent", "CL1", "claudeAgent", "Pro", "eb4325", [
            Window("five_hour", "session", "5h", 37, NOW + 3600, 300),
            Window("seven_day", "weekly", "7d", 91, NOW + 86400, 10080),
        ], checked_at=NOW - 60)
        base = dict(accounts=[acct], activity=Activity("running", "claudeAgent", "claude-opus-5-5", 1, NOW - 20))
        base.update(kw)
        return State(**base)

    def test_shape_and_pressure(self):
        p = build_payload(self.state(), NOW, PRICING, self.settings(), 7)
        self.assertEqual(p["v"], 1)
        self.assertEqual(p["hi"], {"u": 91, "p": "CL1", "w": "7d"})
        self.assertEqual(p["act"], {"s": "run", "p": "CL1", "m": "opus-5-5", "t": 20})
        self.assertEqual(p["acc"][0]["w"][0], {"l": "5h", "u": 37, "r": 3600})
        self.assertLess(len(json.dumps(p, separators=(",", ":"))), 2048)

    def test_reset_credits_sent_including_zero(self):
        st = self.state()
        self.assertNotIn("rc", build_payload(st, NOW, PRICING, self.settings())["acc"][0])
        st.accounts[0].reset_credits = 0
        self.assertEqual(build_payload(st, NOW, PRICING, self.settings())["acc"][0]["rc"], 0)
        st.accounts[0].reset_credits = 1
        self.assertEqual(build_payload(st, NOW, PRICING, self.settings())["acc"][0]["rc"], 1)

    def test_expired_window_retains_last_measured_usage(self):
        st = self.state()
        st.accounts[0].windows[0].resets_at = NOW - 5
        p = build_payload(st, NOW, PRICING, self.settings())
        self.assertEqual(p["acc"][0]["w"][0], {"l": "5h", "u": 37, "r": 0})

    def test_unreported_percent_is_minus_one(self):
        st = self.state()
        st.accounts[0].windows[0].used_percent = None
        p = build_payload(st, NOW, PRICING, self.settings())
        self.assertEqual(p["acc"][0]["w"][0]["u"], -1)

    def test_stale_accounts_flagged_and_excluded_from_pressure(self):
        st = self.state()
        st.accounts[0].checked_at = NOW - 3 * 3600
        p = build_payload(st, NOW, PRICING, self.settings())
        self.assertEqual(p["acc"][0]["st"], 1)
        self.assertNotIn("hi", p)

    def test_costs_tokens_and_unpriced(self):
        recs = [
            UsageRecord(NOW - 60, "claudeAgent", "m-priced", 1000, 10000, 0, 100),
            UsageRecord(NOW - 60, "claudeAgent", "m-unknown", 50, 0, 0, 5),
        ]
        p = build_payload(self.state(records=recs), NOW, PRICING, self.settings())
        # 1000*1e-6 + 10000*1e-7 + 100*1e-5 = 0.003 USD -> 0 cents (rounded); tokens still counted
        self.assertEqual(p["use"]["o1"], 105)
        self.assertEqual(p["use"]["unp"], 1)
        self.assertEqual(len(p["use"]["h"]), 24)

    def test_source_errors_and_openrouter_errors_are_reported(self):
        st = self.state(errors={"t3_limits": "OSError"}, openrouter=openrouter.OpenRouterStatus(NOW - 5, error="offline"))
        p = build_payload(st, NOW, PRICING, self.settings())
        self.assertEqual(p["ok"], 0)
        self.assertEqual(p["err"], "t3_limits")
        self.assertEqual(p["or"], {"x": "offline", "age": 5})

    def test_no_data_at_all(self):
        p = build_payload(State(), NOW, PRICING, self.settings())
        self.assertEqual(p["act"], {"s": "na"})
        self.assertEqual(p["acc"], [])
        self.assertNotIn("hi", p)
        self.assertEqual(p["or"], {"x": "pending"})

    def test_short_model(self):
        self.assertEqual(short_model("claude-opus-5-5"), "opus-5-5")
        self.assertEqual(short_model("openrouter/google/gemma:free"), "gemma")


if __name__ == "__main__":
    unittest.main()
