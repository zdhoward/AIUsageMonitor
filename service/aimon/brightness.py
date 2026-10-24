"""Worker-owned solar cache; payload reads only memory.

Powered by SunriseSunset.io https://sunrisesunset.io
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import log
from .config import Settings

MAX_BYTES = 65536


class BrightnessConfigError(ValueError):
    pass


class BrightnessController:
    def __init__(self, settings: Settings):
        self.s = settings
        if type(settings.auto_brightness_enabled) is not bool:
            raise BrightnessConfigError("auto_brightness_enabled must be a boolean")
        self.enabled = settings.auto_brightness_enabled
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._days = {}
        self._duty = None
        self._source = "startup"
        self._source_date = None
        self._error = None
        self._last_fetch = None
        self._next_fetch = 0.0
        self._retry_until = 0.0
        self._fetch_date = None
        self.tz = None
        self.cache_path = None
        if not self.enabled:
            return
        self._validate()
        self._location = [settings.auto_brightness_lat, settings.auto_brightness_lng, settings.auto_brightness_tz]
        key = hashlib.sha256(json.dumps(self._location).encode()).hexdigest()[:20]
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache")))
        self.cache_path = root / "AIUsageMonitor" / "cache" / f"sun-{key}.json"
        self._load_cache()

    def _validate(self):
        s = self.s
        def number(name, low, high, integer=False):
            v = getattr(s, name)
            if (type(v) not in (int, float) or (integer and type(v) is not int)
                    or not math.isfinite(v) or not low <= v <= high):
                raise BrightnessConfigError(f"{name} must be {'an integer' if integer else 'finite'} in {low}..{high}")
        number("auto_brightness_lat", -90, 90)
        number("auto_brightness_lng", -180, 180)
        for name in ("day", "night", "startup"):
            number(f"auto_brightness_{name}_duty", 0, 255, True)
        if s.auto_brightness_night_duty > s.auto_brightness_day_duty:
            raise BrightnessConfigError("auto_brightness_night_duty must not exceed day duty")
        number("auto_brightness_transition_duration", 0, 1440, True)
        number("auto_brightness_smoothing_duration", 0, 60000, True)
        for name in ("refresh_s", "retry_s", "http_timeout_s", "worker_tick_s"):
            number("auto_brightness_" + name, 0.1, 604800 if name in ("refresh_s", "retry_s") else 300)
        try:
            if not isinstance(s.auto_brightness_tz, str):
                raise ValueError("expected IANA timezone string")
            self.tz = ZoneInfo(s.auto_brightness_tz)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as e:
            raise BrightnessConfigError(f"auto_brightness_tz invalid: {e}; install tzdata on Windows") from e

    def _today(self, now):
        return datetime.fromtimestamp(now, self.tz).date()

    @staticmethod
    def _epoch(value):
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError("invalid solar epoch")
        n = float(value)
        if not math.isfinite(n) or n <= 0 or not n.is_integer():
            raise ValueError("invalid solar epoch")
        return int(n)

    def _day(self, item, expected):
        if not isinstance(item, dict) or item.get("date") != expected.isoformat():
            raise ValueError("solar date mismatch")
        # Unix API item timezone is UTC; top-level tzid is the requested zone.
        if item.get("timezone") not in ("UTC", self.s.auto_brightness_tz):
            raise ValueError("solar timezone mismatch")
        status = item.get("sun_status")
        if status not in ("normal", "midnight_sun", "polar_night"):
            raise ValueError("invalid sun_status")
        rise, setting = self._epoch(item.get("sunrise")), self._epoch(item.get("sunset"))
        if status == "normal":
            if rise is None or setting is None or rise == setting:
                raise ValueError("normal day requires distinct solar events")
            if self._today(rise) != expected:
                raise ValueError("sunrise outside configured local date")
            if self._today(setting) not in (expected, expected + timedelta(days=1)):
                raise ValueError("sunset outside configured local date or following midnight")
        elif rise is not None or setting is not None:
            raise ValueError("polar day requires null solar events")
        return dict(date=expected.isoformat(), timezone=item["timezone"],
                    sun_status=status, sunrise=rise, sunset=setting)

    def _load_cache(self):
        try:
            with self.cache_path.open("rb") as f:
                raw = f.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("cache too large")
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get("location") != self._location:
                raise ValueError("cache location mismatch")
            days = data.get("days")
            if not isinstance(days, dict) or len(days) > 9:
                raise ValueError("invalid cache days")
            today = self._today(time.time())
            clean = {}
            for key, item in days.items():
                d = date.fromisoformat(key)
                entry = self._day(item, d)
                if today - timedelta(days=1) <= d <= today + timedelta(days=7):
                    clean[key] = entry
            self._days = clean
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, OverflowError, RecursionError) as e:
            self._error = f"cache load: {e}"

    def _save_cache(self, days):
        tmp = None
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.cache_path.parent,
                                             prefix="sun-", suffix=".tmp", delete=False) as f:
                tmp = Path(f.name)
                json.dump({"location": self._location, "days": days}, f, separators=(",", ":"))
            os.replace(tmp, self.cache_path)
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)

    def _fetch(self, today):
        first, last = today - timedelta(days=1), today + timedelta(days=7)
        query = urllib.parse.urlencode(dict(lat=self.s.auto_brightness_lat, lng=self.s.auto_brightness_lng,
            date_start=first.isoformat(), date_end=last.isoformat(), timezone=self.s.auto_brightness_tz,
            time_format="unix"))
        request = urllib.request.Request("https://api.sunrisesunset.io/json?" + query,
                                         headers={"User-Agent": "AIUsageMonitor"})
        with urllib.request.urlopen(request, timeout=self.s.auto_brightness_http_timeout_s) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("solar response too large")
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("status") != "OK":
            raise ValueError(f"solar API status: {data.get('status') if isinstance(data, dict) else 'invalid'}")
        if data.get("tzid") != self.s.auto_brightness_tz:
            raise ValueError("solar API tzid mismatch")
        results = data.get("results")
        if not isinstance(results, list) or len(results) != 9:
            raise ValueError("solar API requires nine dates")
        days = {}
        for item in results:
            if not isinstance(item, dict):
                raise ValueError("invalid solar result")
            d = date.fromisoformat(item.get("date", ""))
            if not first <= d <= last or d.isoformat() in days:
                raise ValueError("solar API unexpected/duplicate date")
            days[d.isoformat()] = self._day(item, d)
        return days

    def _compute(self, now, today):
        cur = self._days.get(today.isoformat())
        if cur is None:
            if self._duty is not None:
                self._source = "held"
            return
        s = self.s
        if cur["sun_status"] != "normal":
            day = cur["sun_status"] == "midnight_sun"
            duty, source = (s.auto_brightness_day_duty if day else s.auto_brightness_night_duty), cur["sun_status"]
        else:
            events = sorted((item[k], k == "sunrise")
                for delta in (-1, 0, 1)
                for item in [self._days.get((today + timedelta(days=delta)).isoformat())]
                if item is not None and item["sun_status"] == "normal"
                for k in ("sunrise", "sunset"))
            half = s.auto_brightness_transition_duration * 30.0
            # Clip every centred window to adjacent event midpoints: no ramp
            # overlap, including daylight/night gaps across local midnight.
            is_day = not events[0][1]
            duty = s.auto_brightness_day_duty if is_day else s.auto_brightness_night_duty
            source = "day" if is_day else "night"
            for i, (stamp, rising) in enumerate(events):
                radius = half
                if i:
                    radius = min(radius, (stamp - events[i-1][0]) / 2)
                if i + 1 < len(events):
                    radius = min(radius, (events[i+1][0] - stamp) / 2)
                start, end = stamp - radius, stamp + radius
                before = s.auto_brightness_night_duty if rising else s.auto_brightness_day_duty
                after = s.auto_brightness_day_duty if rising else s.auto_brightness_night_duty
                if now < start:
                    break
                if end > start and now < end:
                    x = (now - start) / (end - start)
                    x = x * x * (3 - 2 * x)
                    duty, source = round(before + (after - before) * x), "transition"
                    break
                duty, source = after, "day" if rising else "night"
        self._duty, self._source, self._source_date = duty, source, today.isoformat()

    def current_duty(self, now_ts=None):
        if not self.enabled:
            return self.s.auto_brightness_startup_duty, "disabled"
        now = time.time() if now_ts is None else now_ts
        with self._lock:
            self._compute(now, self._today(now))
            return self.s.auto_brightness_startup_duty if self._duty is None else self._duty, self._source

    def refresh(self):
        today, mono = self._today(time.time()), time.monotonic()
        with self._lock:
            missing = any((today + timedelta(days=i)).isoformat() not in self._days for i in range(-1, 8))
        if mono >= self._retry_until and (missing or today != self._fetch_date or mono >= self._next_fetch):
            try:
                days = self._fetch(today)
                with self._lock:
                    self._days = days
                    self._last_fetch = time.time()
                    self._error = None
                self._fetch_date = today
                self._next_fetch = time.monotonic() + self.s.auto_brightness_refresh_s
                self._save_cache(days)
            except Exception as e:
                self._retry_until = time.monotonic() + self.s.auto_brightness_retry_s
                with self._lock:
                    self._error = str(e)[:200]
                log.warn("brightness.refresh_failed", detail=str(e)[:200])
        # Failed HTTP must never prevent advancing a valid cached ramp.
        self.current_duty()

    def _worker(self):
        while not self._stop.is_set():
            self.refresh()
            self._stop.wait(self.s.auto_brightness_worker_tick_s)

    def start(self):
        if self.enabled and self._thread is None:
            self._thread = threading.Thread(target=self._worker, name="brightness", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.s.auto_brightness_http_timeout_s + 1)

    def status(self):
        with self._lock:
            if self.enabled:
                self._compute(time.time(), self._today(time.time()))
            duty = self.s.auto_brightness_startup_duty if self._duty is None else self._duty
            source = self._source if self.enabled else "disabled"
            return dict(enabled=self.enabled, mode="automatic" if self.enabled else "disabled",
                current_duty=duty if self.enabled else None, current_source=source, source_date=self._source_date,
                cache_date_available=self.enabled and self._today(time.time()).isoformat() in self._days,
                cache_entries=len(self._days), cache_path=str(self.cache_path) if self.cache_path else None,
                last_fetch_at=self._last_fetch, error=self._error,
                configuration={k: v for k, v in vars(self.s).items() if k.startswith("auto_brightness_")},
                times_source="SunriseSunset.io", attribution_url="https://sunrisesunset.io")


def build_brightness_payload(controller):
    if not controller.enabled:
        return {}
    duty, _ = controller.current_duty()
    return {"bl": duty, "bl_ms": controller.s.auto_brightness_smoothing_duration}


def build_brightness_status(controller):
    return controller.status()
