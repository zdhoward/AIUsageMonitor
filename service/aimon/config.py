"""Service settings. Defaults fit this PC; override with aimon.config.json or AIMON_* env vars."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path

HOME = Path.home()


@dataclass
class Settings:
    # HTTP API. Localhost only unless you deliberately enable Wi-Fi mode.
    bind_host: str = "127.0.0.1"
    bind_port: int = 8797

    # USB serial push to the display. "auto" finds a CH340/CP210x/FTDI bridge.
    serial_port: str = "auto"
    serial_baud: int = 115200
    serial_enabled: bool = True
    push_interval_s: float = 5.0
    mint_metrics_enabled: bool = False

    # Refresh cadence per source (seconds).
    # quota_refresh_s is the lightweight pass (quota caches, activity, codex
    # rate limits); refresh_s is the heavy pass (transcript discovery and
    # aggregation, OpenCode history). Both are clamped away from zero so a bad
    # value cannot spin the loop.
    quota_refresh_s: float = 2.0
    refresh_s: float = 10.0
    opencode_refresh_s: float = 30.0
    openrouter_refresh_s: float = 600.0
    # How long a transcript directory listing is reused before walking again.
    transcript_discovery_s: float = 30.0

    # Keep dashboards awake while a known window with remaining quota resets
    # within this interval. 0 disables the advanced warning (due windows only).
    reset_warning_s: int = 3600

    # Bounded local quota transition log (logs/quota_history.jsonl, ignored).
    quota_history_entries: int = 400

    # Data older than this is flagged stale on the display.
    limits_stale_s: float = 60 * 60

    # Direct read-only Antigravity (Gemini) quota probe using the stored T3
    # login. T3's antigravity cache only reports the Claude & GPT shared 3p
    # allowance, so the direct source replaces it. Five-minute cadence.
    antigravity_enabled: bool = True
    antigravity_refresh_s: float = 300.0
    antigravity_timeout_s: float = 8.0

    # Ignore T3 runs stuck in "running" for longer than this (crashed turns).
    max_run_age_s: float = 6 * 3600

    t3_home: Path = HOME / ".t3"
    opencode_db: Path = HOME / ".local" / "share" / "opencode" / "opencode.db"
    log_dir: Path = Path(__file__).resolve().parents[2] / "logs"
    history_days: int = 7
    openrouter_enabled: bool = True
    extra_free_providers: list[str] = field(default_factory=list)

    # Location-based automatic backlight brightness (optional)
    auto_brightness_enabled: bool = True
    auto_brightness_lat: float = 51.4779
    auto_brightness_lng: float = -0.0015
    auto_brightness_tz: str = "Europe/London"
    auto_brightness_day_duty: int = 255
    auto_brightness_night_duty: int = 40
    auto_brightness_startup_duty: int = 80
    auto_brightness_transition_duration: int = 60
    auto_brightness_smoothing_duration: int = 1000
    auto_brightness_refresh_s: float = 86400.0
    auto_brightness_retry_s: float = 900.0
    auto_brightness_http_timeout_s: float = 5.0
    auto_brightness_worker_tick_s: float = 60.0

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        s = cls()
        path = path or Path(__file__).resolve().parents[1] / "aimon.config.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for f in fields(cls):
                if f.name in data:
                    if f.name.startswith("auto_brightness_"):
                        setattr(s, f.name, _brightness_coerce(f.default, data[f.name], f.name))
                    else:
                        setattr(s, f.name, _coerce(getattr(s, f.name), data[f.name]))
        for f in fields(cls):
            env = os.environ.get("AIMON_" + f.name.upper())
            if env is not None:
                if f.name.startswith("auto_brightness_"):
                    try:
                        value = env if isinstance(f.default, str) else json.loads(env)
                        setattr(s, f.name, _brightness_coerce(f.default, value, f.name))
                    except ValueError as e:
                        raise ValueError(f"AIMON_{f.name.upper()}: {e}") from e
                else:
                    setattr(s, f.name, _coerce(getattr(s, f.name), env))
        return s


def _brightness_coerce(current, value, name):
    expected = type(current)
    valid = type(value) is expected or (expected is float and type(value) is int)
    if not valid:
        raise ValueError(f"{name} expected {expected.__name__}, got {type(value).__name__}")
    return value


def _coerce(current, value):
    if isinstance(current, bool):
        return value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
    if isinstance(current, int):
        return int(value)
    if isinstance(current, float):
        return float(value)
    if isinstance(current, Path):
        return Path(os.path.expanduser(str(value)))
    if isinstance(current, list):
        return value if isinstance(value, list) else [v.strip() for v in str(value).split(",") if v.strip()]
    return value
