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

    # Refresh cadence per source (seconds).
    refresh_s: float = 10.0
    opencode_refresh_s: float = 30.0
    openrouter_refresh_s: float = 600.0

    # Data older than this is flagged stale on the display.
    limits_stale_s: float = 20 * 60

    # Ignore T3 runs stuck in "running" for longer than this (crashed turns).
    max_run_age_s: float = 6 * 3600

    t3_home: Path = HOME / ".t3"
    opencode_db: Path = HOME / ".local" / "share" / "opencode" / "opencode.db"
    log_dir: Path = Path(__file__).resolve().parents[2] / "logs"
    history_days: int = 7
    openrouter_enabled: bool = True
    extra_free_providers: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        s = cls()
        path = path or Path(__file__).resolve().parents[1] / "aimon.config.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for f in fields(cls):
                if f.name in data:
                    setattr(s, f.name, _coerce(getattr(s, f.name), data[f.name]))
        for f in fields(cls):
            env = os.environ.get("AIMON_" + f.name.upper())
            if env is not None:
                setattr(s, f.name, _coerce(getattr(s, f.name), env))
        return s


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
