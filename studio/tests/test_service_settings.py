"""Unit tests for Studio service settings and public release hardening (T-024).

Verifies defaults, allowlist enforcement, secret preservation, validation bounds,
safe failure on malformed configs, atomic replacement, and HTTP write security.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from studio import service_settings
from studio.server import Handler


class TestServiceSettingsDefaultsAndAllowlist(unittest.TestCase):
    def test_default_settings_keys_and_types(self):
        defaults = service_settings.get_default_settings()
        self.assertEqual(set(defaults.keys()), set(service_settings.ALLOWLIST.keys()))
        self.assertEqual(len(defaults), 14)

        # Disallow sensitive internal settings from being exposed
        for forbidden in ("bind_host", "bind_port", "openrouter_api_key", "t3_home", "opencode_db", "log_dir"):
            self.assertNotIn(forbidden, defaults)

        # Check types of defaults
        self.assertIsInstance(defaults["serial_port"], str)
        self.assertIsInstance(defaults["auto_brightness_enabled"], bool)
        self.assertIsInstance(defaults["auto_brightness_lat"], (int, float))
        self.assertIsInstance(defaults["auto_brightness_lng"], (int, float))
        self.assertIsInstance(defaults["auto_brightness_tz"], str)
        self.assertIsInstance(defaults["auto_brightness_day_duty"], int)
        self.assertIsInstance(defaults["auto_brightness_night_duty"], int)
        self.assertIsInstance(defaults["auto_brightness_startup_duty"], int)
        self.assertIsInstance(defaults["auto_brightness_transition_duration"], int)
        self.assertIsInstance(defaults["auto_brightness_smoothing_duration"], int)
        self.assertIsInstance(defaults["limits_stale_s"], (int, float))
        self.assertIsInstance(defaults["reset_warning_s"], int)
        self.assertIsInstance(defaults["quota_refresh_s"], (int, float))
        self.assertIsInstance(defaults["refresh_s"], (int, float))

    def test_get_service_settings_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent = Path(tmpdir) / "aimon.config.json"
            res = service_settings.get_service_settings(non_existent)
            defaults = service_settings.get_default_settings()
            self.assertEqual(res, defaults)

    def test_get_service_settings_filters_secrets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / "aimon.config.json"
            cfg.write_text(
                json.dumps({
                    "openrouter_api_key": "fixture",
                    "bind_host": "0.0.0.0",
                    "t3_home": "/secret/home/path",
                    "serial_port": "COM7",
                    "custom_private_flag": True,
                }),
                encoding="utf-8",
            )
            res = service_settings.get_service_settings(cfg)
            self.assertEqual(res["serial_port"], "COM7")
            self.assertNotIn("openrouter_api_key", res)
            self.assertNotIn("bind_host", res)
            self.assertNotIn("t3_home", res)
            self.assertNotIn("custom_private_flag", res)
            self.assertEqual(set(res.keys()), set(service_settings.ALLOWLIST.keys()))


class TestServiceSettingsMergeAndPreserve(unittest.TestCase):
    def test_save_preserves_secret_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / "aimon.config.json"
            original_data = {
                "openrouter_api_key": "fixture",
                "bind_host": "127.0.0.1",
                "bind_port": 8797,
                "custom_unknown_option": {"nested": "value", "count": 42},
                "serial_port": "COM1",
                "quota_refresh_s": 2.0,
            }
            cfg.write_text(json.dumps(original_data, indent=2), encoding="utf-8")

            updates = {
                "serial_port": "COM9",
                "quota_refresh_s": 4.5,
                "auto_brightness_day_duty": 200,
            }
            returned = service_settings.save_service_settings(updates, config_path=cfg)

            # Returned dict must only expose allowlisted fields
            self.assertEqual(returned["serial_port"], "COM9")
            self.assertEqual(returned["quota_refresh_s"], 4.5)
            self.assertEqual(returned["auto_brightness_day_duty"], 200)
            self.assertNotIn("openrouter_api_key", returned)
            self.assertNotIn("custom_unknown_option", returned)

            # Read raw file from disk directly to verify preservation
            disk_data = json.loads(cfg.read_text(encoding="utf-8"))
            self.assertEqual(disk_data["serial_port"], "COM9")
            self.assertEqual(disk_data["quota_refresh_s"], 4.5)
            self.assertEqual(disk_data["auto_brightness_day_duty"], 200)
            self.assertEqual(disk_data["openrouter_api_key"], "fixture")
            self.assertEqual(disk_data["bind_host"], "127.0.0.1")
            self.assertEqual(disk_data["bind_port"], 8797)
            self.assertEqual(disk_data["custom_unknown_option"], {"nested": "value", "count": 42})


class TestServiceSettingsValidation(unittest.TestCase):
    def test_reject_unknown_fields(self):
        with self.assertRaises(ValueError) as ctx:
            service_settings.validate_settings({"openrouter_api_key": "forbidden"})
        self.assertIn("Unknown settings field", str(ctx.exception))

    def test_reject_wrong_types(self):
        invalid_types = [
            {"serial_port": 12345},
            {"auto_brightness_enabled": "true"},
            {"auto_brightness_enabled": 1},
            {"auto_brightness_lat": "not_a_number"},
            {"auto_brightness_lng": None},
            {"auto_brightness_tz": 100},
            {"auto_brightness_day_duty": "255"},
            {"auto_brightness_day_duty": True},  # bool is subclass of int in python
            {"quota_refresh_s": "fast"},
        ]
        for item in invalid_types:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    service_settings.validate_settings(item)

    def test_reject_nonfinite_numbers(self):
        nan_inf_cases = [
            {"auto_brightness_lat": float("nan")},
            {"auto_brightness_lat": float("inf")},
            {"auto_brightness_lat": float("-inf")},
            {"auto_brightness_lng": float("nan")},
            {"limits_stale_s": float("nan")},
            {"quota_refresh_s": float("inf")},
            {"refresh_s": float("-inf")},
        ]
        for item in nan_inf_cases:
            with self.subTest(item=item):
                with self.assertRaises(ValueError) as ctx:
                    service_settings.validate_settings(item)
                self.assertIn("finite number", str(ctx.exception))

    def test_reject_out_of_range_numbers(self):
        out_of_range = [
            {"auto_brightness_lat": 90.1},
            {"auto_brightness_lat": -90.1},
            {"auto_brightness_lng": 180.1},
            {"auto_brightness_lng": -180.1},
            {"auto_brightness_day_duty": 256},
            {"auto_brightness_day_duty": -1},
            {"auto_brightness_night_duty": 300},
            {"auto_brightness_startup_duty": -5},
            {"auto_brightness_transition_duration": -1},
            {"auto_brightness_smoothing_duration": -10},
            {"auto_brightness_smoothing_duration": 600001},
            {"limits_stale_s": 5.0},  # min 10
            {"limits_stale_s": 3000000.0},
            {"reset_warning_s": -1},
            {"quota_refresh_s": 0.2},  # min 0.5
            {"refresh_s": 0.9},  # min 1.0
        ]
        for item in out_of_range:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    service_settings.validate_settings(item)

    def test_timezone_validation(self):
        # Valid zones
        valid_zones = ["Europe/London", "America/New_York", "UTC", "Asia/Tokyo"]
        for tz in valid_zones:
            with self.subTest(tz=tz):
                validated = service_settings.validate_settings({"auto_brightness_tz": tz})
                self.assertEqual(validated["auto_brightness_tz"], tz)

        # Invalid zones
        invalid_zones = ["Invalid/Timezone", "Mars/Phobos", "", "   ", "NotATimezone"]
        for tz in invalid_zones:
            with self.subTest(tz=tz):
                with self.assertRaises(ValueError):
                    service_settings.validate_settings({"auto_brightness_tz": tz})

    def test_serial_port_validation(self):
        valid_ports = ["auto", "COM3", "COM15", "/dev/ttyUSB0", "/dev/ttyACM0"]
        for port in valid_ports:
            with self.subTest(port=port):
                validated = service_settings.validate_settings({"serial_port": port})
                self.assertEqual(validated["serial_port"], port)

        invalid_ports = [
            "",
            "   ",
            "A" * 65,
            "COM1\nDROP TABLE",
            "COM1\r\n",
            "COM\x00NULL",
        ]
        for port in invalid_ports:
            with self.subTest(port=port):
                with self.assertRaises(ValueError):
                    service_settings.validate_settings({"serial_port": port})


class TestServiceSettingsMalformedConfig(unittest.TestCase):
    def test_service_brightness_limits_match(self):
        for key, value in (("auto_brightness_transition_duration", 1441),
                           ("auto_brightness_smoothing_duration", 60001),
                           ("reset_warning_s", 1.5)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                service_settings.validate_settings({key: value})

    def test_night_cannot_exceed_day(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / 'config.json'
            cfg.write_text('{"auto_brightness_day_duty":100}', encoding='utf-8')
            with self.assertRaises(ValueError):
                service_settings.save_service_settings({'auto_brightness_night_duty':101}, cfg)
            self.assertEqual(json.loads(cfg.read_text())['auto_brightness_day_duty'],100)

    def test_malformed_existing_file_fails_safely_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / "aimon.config.json"
            malformed_content = '{"broken": [json, not_valid}'
            cfg.write_text(malformed_content, encoding="utf-8")

            # GET should raise ValueError safely without crashing or overwriting
            with self.assertRaises(ValueError):
                service_settings.get_service_settings(cfg)

            # SAVE must refuse to overwrite malformed existing file
            with self.assertRaises(ValueError) as ctx:
                service_settings.save_service_settings({"serial_port": "COM5"}, config_path=cfg)
            self.assertIn("refusing to overwrite", str(ctx.exception))

            # Verify file content is completely untouched
            self.assertEqual(cfg.read_text(encoding="utf-8"), malformed_content)


class TestServiceSettingsAtomicWriteFailure(unittest.TestCase):
    def test_atomic_write_failure_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / "aimon.config.json"
            initial_content = '{\n  "serial_port": "COM1"\n}\n'
            cfg.write_text(initial_content, encoding="utf-8")

            with patch("os.replace", side_effect=OSError("Disk full / permission denied")):
                with self.assertRaises(OSError):
                    service_settings.save_service_settings({"serial_port": "COM2"}, config_path=cfg)

            # File must remain with initial content
            self.assertEqual(cfg.read_text(encoding="utf-8"), initial_content)

            # Temp file must have been cleaned up
            leftover_tmps = list(Path(tmpdir).glob(".*.tmp"))
            self.assertEqual(leftover_tmps, [])


class DummyHandler:
    """Helper to test Handler.check_write_security and Handler.body without starting a server."""
    def __init__(self, headers: dict[str, str], body_bytes: bytes = b""):
        self.headers = headers
        self.rfile = io.BytesIO(body_bytes)

    check_write_security = Handler.check_write_security
    body = Handler.body


class TestHandlerSecurityAndBodyBound(unittest.TestCase):
    def test_allowed_loopback_hosts_and_origins(self):
        for host in ("127.0.0.1:8798", "localhost:8798", "[::1]:8798"):
            for origin in ("http://" + host, None):
                headers = {
                    "Content-Type": "application/json",
                    "Host": host,
                }
                if origin is not None:
                    headers["Origin"] = origin
                handler = DummyHandler(headers)
                # Should not raise
                handler.check_write_security()

    def test_reject_hostile_host(self):
        hostile_hosts = ["evil.com", "attacker.io:8798", "192.168.1.100", "my-server.local"]
        for host in hostile_hosts:
            with self.subTest(host=host):
                handler = DummyHandler({
                    "Content-Type": "application/json",
                    "Host": host,
                    "Origin": "http://127.0.0.1:8798",
                })
                with self.assertRaises(PermissionError):
                    handler.check_write_security()

    def test_reject_hostile_origin(self):
        hostile_origins = ["http://evil.com", "https://malicious.org", "http://attacker:8798", "http://127.0.0.1:3000", "http://localhost:8798", "https://127.0.0.1:8798"]
        for origin in hostile_origins:
            with self.subTest(origin=origin):
                handler = DummyHandler({
                    "Content-Type": "application/json",
                    "Host": "127.0.0.1:8798",
                    "Origin": origin,
                })
                with self.assertRaises(PermissionError) as ctx:
                    handler.check_write_security()
                self.assertIn("Cross-origin", str(ctx.exception))

    def test_reject_hostile_referer(self):
        handler = DummyHandler({
            "Content-Type": "application/json",
            "Host": "127.0.0.1:8798",
            "Referer": "http://evil.com/exploit",
        })
        with self.assertRaises(PermissionError) as ctx:
            handler.check_write_security()
        self.assertIn("Cross-origin referer", str(ctx.exception))

    def test_reject_invalid_content_type(self):
        for ct in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data", ""):
            with self.subTest(ct=ct):
                handler = DummyHandler({
                    "Content-Type": ct,
                    "Host": "127.0.0.1:8798",
                })
                with self.assertRaises(ValueError) as ctx:
                    handler.check_write_security()
                self.assertIn("Content-Type must be application/json", str(ctx.exception))

    def test_body_bound_size_and_malformed(self):
        # Missing Content-Length
        handler = DummyHandler({})
        with self.assertRaises(ValueError) as ctx:
            handler.body()
        self.assertIn("Missing Content-Length", str(ctx.exception))

        # Negative Content-Length
        handler = DummyHandler({"Content-Length": "-5"})
        with self.assertRaises(ValueError) as ctx:
            handler.body()
        self.assertIn("Negative Content-Length", str(ctx.exception))

        # Exceeds max_size
        handler = DummyHandler({"Content-Length": "1000"}, body_bytes=b"x" * 1000)
        with self.assertRaises(ValueError) as ctx:
            handler.body(max_size=500)
        self.assertIn("Request body too large", str(ctx.exception))

        # Malformed JSON
        handler = DummyHandler({"Content-Length": "10"}, body_bytes=b"{invalid:}")
        with self.assertRaises(ValueError) as ctx:
            handler.body()
        self.assertIn("Malformed JSON body", str(ctx.exception))

        # JSON body not an object
        handler = DummyHandler({"Content-Length": "4"}, body_bytes=b"[12]")
        with self.assertRaises(ValueError) as ctx:
            handler.body()
        self.assertIn("JSON body must be an object", str(ctx.exception))

        # Valid JSON body
        payload = b'{"serial_port": "auto"}'
        handler = DummyHandler({"Content-Length": str(len(payload))}, body_bytes=payload)
        parsed = handler.body()
        self.assertEqual(parsed, {"serial_port": "auto"})


if __name__ == "__main__":
    unittest.main()
