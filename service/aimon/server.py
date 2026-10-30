"""Local HTTP API and the background refresh loop.

GET  /v1/device   compact payload the firmware renders (same as the serial push)
GET  /v1/status   richer JSON for debugging
GET  /healthz     liveness + serial link state
POST /v1/serial/pause?seconds=N   release the COM port (used by the flash script)
POST /v1/serial/resume
"""

from __future__ import annotations

import json
import math
import ipaddress
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import log
from .brightness import BrightnessController, build_brightness_payload, build_brightness_status
from .config import Settings
from .companion import Companion, LocalMetrics
from .serial_link import SerialLink
from .snapshot import Collector, build_payload, build_status
from .sources.cpamc import CpamcSource

# Refresh and push delays are clamped so a zero, negative or tiny configured
# value cannot spin the loop.
MIN_REFRESH_S = 0.25


def _interval(value, default: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    if value != value:  # NaN
        return default
    return max(value, MIN_REFRESH_S)


class App:
    def __init__(self, settings: Settings):
        self.s = settings
        self.collector = Collector(settings)
        self.started = time.time()
        self._seq = 0
        self._payload_lock = threading.Lock()
        self.companion = Companion()
        self._behavior_wake = threading.Event()
        self._stop = threading.Event()
        self.serial: SerialLink | None = None
        self.brightness = BrightnessController(settings)
        self.cpamc = CpamcSource()
        threading.Thread(target=self.cpamc.run, name="cpamc", daemon=True).start()
        if settings.serial_enabled:
            self.serial = SerialLink(settings.serial_port, settings.serial_baud, settings.push_interval_s,
                                     self.device_payload, self.cpamc.line)

    def device_payload(self) -> dict:
        with self._payload_lock:
            self._seq += 1
            payload = build_payload(self.collector.snapshot(), time.time(), self.collector.pricing, self.s, self._seq)
            mint = self.companion.snapshot()
            if mint:
                payload["mint"] = mint
            # Optional location-based backlight level (0..255). Missing/invalid
            # keeps the current device level; older firmware ignores "bl".
            brightness = build_brightness_payload(self.brightness)
            if brightness:
                payload.update(brightness)
            # Never truncate JSON or transmit a line the firmware will discard.
            if len(json.dumps(payload, separators=(",", ":")).encode()) > 4095:
                payload = {"v": 1, "seq": self._seq, "ok": 0, "err": "payload too large", "mint": mint}
                brightness = build_brightness_payload(self.brightness)
                if brightness:
                    payload.update(brightness)
            return payload

    def behavior_loop(self) -> None:
        metrics = LocalMetrics() if self.s.mint_metrics_enabled else None
        next_sample = 0.0
        while not self._stop.is_set():
            self._behavior_wake.clear()
            now = time.monotonic()
            sample = None
            if metrics and now >= next_sample:
                sample = metrics.sample()
                next_sample = now + 1
            before = self.companion.snapshot(now)
            started = self.companion.tick(now, sample)
            after = self.companion.snapshot(now)
            if self.serial and (started or before is None or before["e"] != after["e"]):
                self.serial.request_push()
            self._behavior_wake.wait(0.25)

    @staticmethod
    def quota_signature(st) -> tuple:
        """Explicit measurements only: age, countdown and check time excluded."""
        return (
            tuple(sorted(st.errors)),
            st.activity.state, st.activity.instance_id, st.activity.model, st.activity.running,
            tuple(
                (a.instance_id, a.source, a.unavailable, a.reset_credits,
                 tuple((w.id, w.kind,
                        w.used_percent if w.used_percent is not None and math.isfinite(w.used_percent) else None,
                        w.resets_at if w.resets_at is not None and math.isfinite(w.resets_at) else None)
                       for w in a.windows))
                for a in st.accounts
            ),
        )

    def refresh_loop(self) -> None:
        heavy_s = _interval(self.s.refresh_s, 10.0)
        light_s = min(_interval(self.s.quota_refresh_s, 2.0), heavy_s)
        next_heavy = time.time() + heavy_s  # serve() already did the first heavy pass
        signature = self.quota_signature(self.collector.snapshot())
        while not self._stop.is_set():
            t0 = time.time()
            heavy = t0 >= next_heavy
            try:
                st = self.collector.refresh(t0, heavy=heavy)
            except Exception as e:
                log.warn("collector.crashed", err=type(e).__name__, detail=str(e)[:160])
                st = self.collector.snapshot()
            log.debug("collector.timing", ms=int((time.time() - t0) * 1000), heavy=int(heavy))
            if heavy:
                next_heavy = time.time() + heavy_s
            # Push only when a quota measurement, reset deadline or activity
            # state actually changed. request_push() is coalesced, so a burst
            # still produces at most one write; the 5-second heartbeat remains.
            current = self.quota_signature(st)
            if current != signature:
                signature = current
                if self.serial:
                    self.serial.request_push()
            # Wake at the next reset as well as the regular polling cadence.
            # Past deadlines use normal polling: an unchanged cache must not spin.
            now = time.time()
            delay = min(light_s, max(next_heavy - now, MIN_REFRESH_S))
            for a in st.accounts:
                for w in a.windows:
                    if w.resets_at is not None and w.resets_at > now:
                        delay = min(delay, w.resets_at - now)
            self._stop.wait(max(delay, MIN_REFRESH_S))

    def health(self) -> dict:
        st = self.collector.snapshot()
        sl = self.serial
        return {
            "ok": True,
            "uptime_s": int(time.time() - self.started),
            "refreshed_at": st.refreshed_at,
            "source_errors": st.errors,
            "brightness": build_brightness_status(self.brightness),
            "serial": None
            if sl is None
            else {
                "port": sl.connected_port,
                "paused": sl.paused,
                "last_push": sl.last_push,
                "last_ack": sl.last_ack,
                "device": sl.device_hello,
            },
        }

    def serve(self) -> None:
        app = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, code: int, body: dict) -> None:
                data = json.dumps(body, separators=(",", ":")).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/v1/device":
                    self._send(200, app.device_payload())
                elif path == "/v1/status":
                    status = build_status(app.collector.snapshot(), time.time())
                    status["brightness"] = build_brightness_status(app.brightness)
                    self._send(200, status)
                elif path == "/healthz":
                    self._send(200, app.health())
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                url = urlparse(self.path)
                if url.path == "/v1/mint/react":
                    if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                        return self._send(403, {"error": "local reactions only"})
                    query = parse_qs(url.query, keep_blank_values=True)
                    if (set(query) != {"action"} or len(query["action"]) != 1
                            or self.headers.get("Content-Length", "0") != "0"
                            or self.headers.get("Transfer-Encoding")):
                        return self._send(400, {"error": "expected one action and empty body"})
                    code = app.companion.request(query["action"][0])
                    app._behavior_wake.set()
                    return self._send(code, {"accepted": code in (200, 202)})
                if app.serial is None:
                    return self._send(409, {"error": "serial disabled"})
                if url.path == "/v1/serial/pause":
                    secs = float((parse_qs(url.query).get("seconds") or ["120"])[0])
                    app.serial.pause(min(max(secs, 1), 900))
                    log.event("serial.pause_requested", seconds=secs)
                    return self._send(200, {"paused_s": secs})
                if url.path == "/v1/serial/resume":
                    app.serial.resume()
                    log.event("serial.resume_requested")
                    return self._send(200, {"resumed": True})
                self._send(404, {"error": "not found"})

            def log_message(self, fmt, *args):
                log.debug("http.request", line=fmt % args)

        httpd = ThreadingHTTPServer((self.s.bind_host, self.s.bind_port), Handler)
        self.httpd = httpd
        try:
            self.collector.refresh()
            self.brightness.start()
            threading.Thread(target=self.behavior_loop, name="mint", daemon=True).start()
            threading.Thread(target=self.refresh_loop, name="refresh", daemon=True).start()
            if self.serial:
                threading.Thread(target=self.serial.run, name="serial", daemon=True).start()
            log.event("service.started", bind=f"{self.s.bind_host}:{httpd.server_port}", serial=self.s.serial_port if self.serial else "off")
            httpd.serve_forever(poll_interval=0.5)
        finally:
            self._stop.set()
            self.brightness.stop()
            if self.serial:
                self.serial.stop()
            httpd.server_close()
            log.event("service.stopped")
