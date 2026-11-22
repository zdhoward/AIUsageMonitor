"""Offline checks for quota observation freshness, independent of link polling."""
import sys
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aimon.sources import cpamc

NOW = 1_795_360_000.0


class QuotaFreshnessTests(unittest.TestCase):
    def setUp(self):
        with patch.object(cpamc, 'load_key', return_value='offline'):
            self.src = cpamc.CpamcSource(base='http://offline.invalid')
        self.src.profiles = {'antigravity': {
            'provider': 'antigravity',
            'request': {'method': 'POST', 'url': 'http://offline.invalid/quota', 'header': {}},
            'windows': [
                {'pool': 'main', 'label': '5h', 'path': 'session', 'remaining': 'left'},
                {'pool': 'main', 'label': '7d', 'path': 'week', 'remaining': 'left'},
            ],
        }}
        self.accounts = [{'auth_index': 'example-1', 'provider': 'antigravity', 'status': 'active'}]
        self.src._call = lambda *a, **kw: {'files': self.accounts}
        self.windows = [{'pool': 'main', 'label': '5h', 'rem': 0, 'reset': NOW+18000, 'len': 18000}]
        self.src._live_one = lambda *a: {'windows': self.windows, 'probe_ok': True}

    def poll(self, at):
        with patch.object(cpamc.time, 'time', return_value=at):
            self.src.poll_once()
            return self.src.line()

    def fail_after_success(self, auth=False):
        self.poll(NOW)
        self.src._live_one = lambda *a: {'windows': None, 'auth_failed': auth}
        return self.poll(NOW+301)

    def test_failure_keeps_zero_and_timestamp_but_warns(self):
        line = self.fail_after_success()
        self.assertEqual(self.src._live['example-1'].get('checked_at'), NOW)
        self.assertEqual(line['g'][0]['p'][0]['w'][0]['r'], 0)
        self.assertEqual((line['qa'], line['qs'], line['attn']), (301, 1, 1))
        self.assertEqual((line['g'][0]['age'], line['g'][0]['st']), (301, 1))

    def test_auth_failure_keeps_last_good_values(self):
        line = self.fail_after_success(auth=True)
        self.assertEqual(line['g'][0]['p'][0]['w'][0]['r'], 0)
        self.assertEqual(line['qs'], 1)

    def test_account_poll_cannot_clear_quota_failure_or_renew_age(self):
        self.fail_after_success()
        line = self.poll(NOW+310)
        self.assertEqual((line['age'], line['qa'], line['qs']), (0, 310, 1))

    def test_recovery_requires_successful_quota_probe(self):
        self.fail_after_success(auth=True)
        self.src._live_one = lambda *a: {'windows': self.windows, 'probe_ok': True}
        line = self.poll(NOW+602)
        self.assertEqual((line['qa'], line['qs'], line['attn']), (0, 0, 0))

    def test_time_alone_expires_reading(self):
        self.poll(NOW)
        with patch.object(cpamc.time, 'time', return_value=NOW+361):
            line = self.src.line()
        self.assertEqual((line['qa'], line['qs']), (361, 1))

    def test_startup_unknown_is_not_zero_age(self):
        self.src._live_one = lambda *a: {'windows': None}
        line = self.poll(NOW)
        self.assertEqual((line['qa'], line['qs'], line['g'][0]['age']), (-1, 1, -1))

    def test_oldest_account_and_disabled_account(self):
        self.poll(NOW)
        self.accounts.append({'auth_index': 'example-2', 'provider': 'antigravity', 'status': 'active'})
        line = self.poll(NOW+100)
        self.assertEqual(line['qa'], 100)
        self.accounts[0]['disabled'] = True
        line = self.poll(NOW+110)
        self.assertEqual((line['qa'], line['g'][0]['c']), (10, 1))

    def test_account_removal_drops_its_age(self):
        self.poll(NOW)
        self.accounts = []
        line = self.poll(NOW+500)
        self.assertEqual(line['g'], [])
        self.assertEqual(line['qs'], 0)

    def test_account_list_outage_preserves_age_and_warns(self):
        self.poll(NOW)
        def fail(*a, **kw):
            raise OSError('offline')
        self.src._call = fail
        line = self.poll(NOW+301)
        self.assertEqual((line['up'], line['qa'], line['qs']), (0, 301, 1))

    def test_success_time_is_after_request_completion(self):
        def complete(*a):
            clock.return_value = NOW+20
            return {'windows': self.windows, 'probe_ok': True}
        self.src._live_one = complete
        with patch.object(cpamc.time, 'time', return_value=NOW) as clock:
            self.src.poll_once()
        self.assertEqual(self.src._live['example-1'].get('checked_at'), NOW+20)

    def test_partial_response_is_not_a_successful_observation(self):
        self.src._call = lambda *a, **kw: {'status_code': 200, 'body': {'session': {'left': 1}}}
        result = cpamc.CpamcSource._live_one(self.src, self.accounts[0], self.src.profiles['antigravity'])
        self.assertIsNone(result['windows'])
        self.assertFalse(result.get('probe_ok', False))

    def test_disabled_optional_bucket_is_not_missing(self):
        profile = self.src.profiles['antigravity']
        profile['windows'][0]['skip_if'] = 'disabled'
        self.src._call = lambda *a, **kw: {'status_code': 200, 'body': {
            'session': {'disabled': True}, 'week': {'left': 0.5}}}
        result = cpamc.CpamcSource._live_one(self.src, self.accounts[0], profile)
        self.assertTrue(result.get('probe_ok'))
        self.assertEqual(len(result['windows']), 1)

    def test_optional_absent_week_is_allowed(self):
        profile = self.src.profiles['antigravity']
        profile['windows'][1]['optional'] = True
        self.src._call = lambda *a, **kw: {'status_code': 200, 'body': {'session': {'left': 1}}}
        result = cpamc.CpamcSource._live_one(self.src, self.accounts[0], profile)
        self.assertTrue(result.get('probe_ok'))
        self.assertEqual(len(result['windows']), 1)

    def test_parser_exception_warns_and_other_account_still_updates(self):
        self.poll(NOW)
        self.accounts.append({'auth_index': 'example-2', 'provider': 'antigravity', 'status': 'active'})
        def probe(acc, profile):
            if acc['auth_index'] == 'example-1':
                raise ValueError('invalid numeric quota')
            return {'windows': self.windows, 'probe_ok': True}
        self.src._live_one = probe
        line = self.poll(NOW+301)
        self.assertEqual(line['qs'], 1)
        self.assertEqual(self.src._live['example-1']['checked_at'], NOW)
        self.assertFalse(self.src._live['example-1']['probe_ok'])
        self.assertEqual(self.src._live['example-2']['checked_at'], NOW+301)

    def test_profiles_allow_real_single_window_plans(self):
        profiles = cpamc.load_profiles()
        bodies = {
            'codex': {'rate_limit': {'primary_window': {'used_percent': 25, 'limit_window_seconds': 2592000}}},
            'claude': {'five_hour': {'utilization': 25}},
            'antigravity': {'groups': [{'buckets': [
                {'bucketId': 'gemini-5h', 'remainingFraction': 0.75},
                {'bucketId': 'gemini-weekly', 'remainingFraction': 0.5}]}]},
        }
        for provider, body in bodies.items():
            with self.subTest(provider=provider):
                self.src._call = lambda *a, **kw: {'status_code': 200, 'body': body}
                result = cpamc.CpamcSource._live_one(self.src, self.accounts[0], profiles[provider])
                self.assertTrue(result.get('probe_ok'))

    def test_health_exposes_failed_quota_even_with_live_usb_ack(self):
        from aimon.server import App
        app = App.__new__(App)
        app.cpamc = self.src
        app.collector = SimpleNamespace(snapshot=lambda: SimpleNamespace(errors={}, refreshed_at=NOW))
        app.serial = SimpleNamespace(connected_port='offline', paused=False, last_push=NOW,
                                     last_ack=NOW, device_hello='offline')
        app.started = NOW
        app.brightness = None
        self.fail_after_success()
        with patch('aimon.server.build_brightness_status', return_value={}):
            health = app.health()
        self.assertIn('cpamc', health['source_errors'])
        self.assertEqual(health['proxy']['qs'], 1)
        self.assertTrue(health['ok'])  # liveness is separate

    def test_claude_inventory_is_forwarded_without_identifiers(self):
        profile = cpamc.load_profiles()['claude']
        body = {'five_hour': {'utilization': 25}, 'cedar_ember': {'eligible': True, 'grants': [
            {'id': 'not-for-display', 'resets_left': 2, 'usable_now': True,
             'ends_at': '2027-01-16T08:00:00Z'}]}}
        self.src._call = lambda *a, **kw: {'status_code': 200, 'body': body}
        with patch.object(cpamc.time, 'time', return_value=NOW):
            result = cpamc.CpamcSource._live_one(self.src, self.accounts[0], profile)
        self.assertEqual(result['rc'], 2)
        self.assertGreater(result['rx'], NOW)
        self.assertNotIn('not-for-display', str(result))

    def test_missing_claude_inventory_keeps_quota_but_unknown_reset_count(self):
        profile = cpamc.load_profiles()['claude']
        self.src._call = lambda *a, **kw: {'status_code': 200, 'body': {'five_hour': {'utilization': 25}}}
        result = cpamc.CpamcSource._live_one(self.src, self.accounts[0], profile)
        self.assertTrue(result['probe_ok'])
        self.assertEqual((result['rc'], result['rx']), (-1, 0))


if __name__ == '__main__':
    unittest.main()
