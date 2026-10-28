"""Service configuration settings reader, validator and atomic writer.

Provides safe access to service/aimon.config.json without starting
background collectors, probes, or accessing credentials.
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading
import uuid
import zoneinfo
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIR = ROOT / "service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

DEFAULT_CONFIG_PATH = SERVICE_DIR / "aimon.config.json"

# Strict allowlist of user-serviceable non-secret fields.
ALLOWLIST: dict[str, type] = {
    "serial_port": str,
    "auto_brightness_enabled": bool,
    "auto_brightness_lat": float,
    "auto_brightness_lng": float,
    "auto_brightness_tz": str,
    "auto_brightness_day_duty": int,
    "auto_brightness_night_duty": int,
    "auto_brightness_startup_duty": int,
    "auto_brightness_transition_duration": int,
    "auto_brightness_smoothing_duration": int,
    "limits_stale_s": float,
    "reset_warning_s": int,
    "quota_refresh_s": float,
    "refresh_s": float,
}

_settings_lock = threading.Lock()


def get_default_settings() -> dict[str, Any]:
    """Return default settings instantiated from the service Settings model."""
    from aimon.config import Settings
    s = Settings()
    return {k: getattr(s, k) for k in ALLOWLIST}


def get_service_settings(config_path: Path | None = None) -> dict[str, Any]:
    """Read service settings, merging defaults with any persisted allowlisted values.

    Never exposes private keys, full config dumps, or system paths.
    """
    path = (config_path or DEFAULT_CONFIG_PATH).resolve()
    defaults = get_default_settings()
    out = dict(defaults)

    if path.exists():
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("Service configuration file must be a JSON object")
        except Exception as e:
            raise ValueError(f"Failed to read service configuration: malformed JSON ({type(e).__name__})") from None

        for k in ALLOWLIST:
            if k in data:
                try:
                    out[k] = _validate_field(k, data[k])
                except ValueError:
                    # Ignore corrupted values in unvalidated external edits, keep default
                    pass

    return out


def _validate_field(k: str, v: Any) -> Any:
    """Validate a single allowlisted setting field."""
    if k not in ALLOWLIST:
        raise ValueError(f"Unknown settings field: '{k}'")

    # Reject non-finite numbers (NaN, Inf)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if not math.isfinite(v):
            raise ValueError(f"Field '{k}' must be a finite number")

    if k == "serial_port":
        if not isinstance(v, str):
            raise ValueError("serial_port must be a string")
        if any(ord(c) < 32 for c in v):
            raise ValueError("serial_port contains invalid control characters")
        s = v.strip()
        if not s:
            raise ValueError("serial_port cannot be empty")
        if len(s) > 64:
            raise ValueError("serial_port cannot exceed 64 characters")
        return s

    if k == "auto_brightness_enabled":
        if not isinstance(v, bool):
            raise ValueError("auto_brightness_enabled must be a boolean")
        return v

    if k == "auto_brightness_lat":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("auto_brightness_lat must be a number")
        val = float(v)
        if not (-90.0 <= val <= 90.0):
            raise ValueError("auto_brightness_lat must be between -90 and 90 degrees")
        return val

    if k == "auto_brightness_lng":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("auto_brightness_lng must be a number")
        val = float(v)
        if not (-180.0 <= val <= 180.0):
            raise ValueError("auto_brightness_lng must be between -180 and 180 degrees")
        return val

    if k == "auto_brightness_tz":
        if not isinstance(v, str):
            raise ValueError("auto_brightness_tz must be a string")
        if any(ord(c) < 32 for c in v):
            raise ValueError("auto_brightness_tz contains invalid control characters")
        s = v.strip()
        if not s:
            raise ValueError("auto_brightness_tz cannot be empty")
        try:
            zoneinfo.ZoneInfo(s)
        except Exception:
            raise ValueError(f"Invalid timezone: '{s}'") from None
        return s

    if k in ("auto_brightness_day_duty", "auto_brightness_night_duty", "auto_brightness_startup_duty"):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"{k} must be an integer")
        val = int(v)
        if float(v) != val:
            raise ValueError(f"{k} must be an integer")
        if not (0 <= val <= 255):
            raise ValueError(f"{k} must be between 0 and 255")
        return val

    if k == "auto_brightness_transition_duration":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("auto_brightness_transition_duration must be a number")
        if int(v) != v:
            raise ValueError("auto_brightness_transition_duration must be an integer")
        val = int(v)
        if not (0 <= val <= 1440):
            raise ValueError("auto_brightness_transition_duration must be between 0 and 1440 minutes")
        return val

    if k == "auto_brightness_smoothing_duration":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("auto_brightness_smoothing_duration must be a number")
        if int(v) != v:
            raise ValueError("auto_brightness_smoothing_duration must be an integer")
        val = int(v)
        if not (0 <= val <= 60000):
            raise ValueError("auto_brightness_smoothing_duration must be between 0 and 60000 ms")
        return val

    if k == "limits_stale_s":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("limits_stale_s must be a number")
        val = float(v)
        if not (10.0 <= val <= 2592000.0):
            raise ValueError("limits_stale_s must be between 10 and 2592000 seconds")
        return val

    if k == "reset_warning_s":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("reset_warning_s must be an integer")
        if int(v) != v:
            raise ValueError("reset_warning_s must be an integer")
        val = int(v)
        if not (0 <= val <= 604800):
            raise ValueError("reset_warning_s must be between 0 and 604800 seconds")
        return val

    if k == "quota_refresh_s":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("quota_refresh_s must be a number")
        val = float(v)
        if not (0.5 <= val <= 86400.0):
            raise ValueError("quota_refresh_s must be between 0.5 and 86400 seconds")
        return val

    if k == "refresh_s":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("refresh_s must be a number")
        val = float(v)
        if not (1.0 <= val <= 86400.0):
            raise ValueError("refresh_s must be between 1.0 and 86400 seconds")
        return val

    raise ValueError(f"Unhandled allowlisted key: '{k}'")


def validate_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Validate incoming settings payload against the allowlist and value constraints."""
    if not isinstance(updates, dict):
        raise ValueError("Settings payload must be a JSON object")

    validated: dict[str, Any] = {}
    for k, v in updates.items():
        if k not in ALLOWLIST:
            raise ValueError(f"Unknown settings field: '{k}'")
        validated[k] = _validate_field(k, v)

    return validated


def save_service_settings(updates: dict[str, Any], config_path: Path | None = None) -> dict[str, Any]:
    """Atomically update allowlisted settings in the service config file.

    Preserves all existing private and unknown keys. Replaces file atomically.
    Fails safely without overwriting if existing JSON is malformed.
    """
    target_path = (config_path or DEFAULT_CONFIG_PATH).resolve()
    validated = validate_settings(updates)

    with _settings_lock:
        existing: dict[str, Any] = {}
        if target_path.exists():
            try:
                content = target_path.read_text(encoding="utf-8")
                loaded = json.loads(content)
                if not isinstance(loaded, dict):
                    raise ValueError("Existing configuration is not a JSON object")
                existing = loaded
            except Exception:
                raise ValueError("Existing service configuration is malformed JSON; refusing to overwrite") from None

        # Preserve all existing keys and merge validated updates
        merged = dict(existing)
        for k, v in validated.items():
            merged[k] = v
        defaults = get_default_settings()
        if merged.get("auto_brightness_night_duty", defaults["auto_brightness_night_duty"]) > merged.get("auto_brightness_day_duty", defaults["auto_brightness_day_duty"]):
            raise ValueError("Night brightness must not exceed day brightness")

        # Atomic replacement in same directory
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            tmp_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp_path, target_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        defaults = get_default_settings()
        return {k: merged.get(k, defaults[k]) for k in ALLOWLIST}
