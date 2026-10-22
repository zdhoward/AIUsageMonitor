"""Local HTTP API and the background refresh loop.

GET  /v1/device   compact payload the firmware renders (same as the serial push)
GET  /v1/status   richer JSON for debugging
GET  /healthz     liveness + serial link state
POST /v1/serial/pause?seconds=N   release the COM port (used by the flash script)
POST /v1/serial/resume
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import log
from .config import Settings
from .serial_link import SerialLink
from .snapshot import Collector, build_payload, build_status


class App:
    def __init__(self, settings: Settings):
        self.s = settings
        self.collector = Collector(settings)
        self.started = time.time()
        self._seq = 0
        self._stop = threading.Event()
        self.serial: SerialLink | None = None
        if settings.serial_enabled:
            self.serial = SerialLink(settings.serial_port, settings.serial_baud, settings.push_interval_s, self.device_payload)

    def device_payload(self) -> dict:
        self._seq += 1
        return build_payload(self.collector.snapshot(), time.time(), self.collector.pricing, self.s, self._seq)

    def refresh_loop(self) -> None:
        while not self._stop.is_set():
            t0 = time.time()
            try:
                self.collector.refresh()
            except Exception as e:
                log.warn("collector.crashed", err=type(e).__name__, detail=str(e)[:160])
            log.debug("collector.timing", ms=int((time.time() - t0) * 1000))
            # Wake at the next reset as well as the regular polling cadence.
            # Past deadlines use normal polling: an unchanged cache must not spin.
            now = time.time()
            deadlines = [
                w.resets_at
                for a in self.collector.snapshot().accounts
                for w in a.windows
                if w.resets_at is not None and w.resets_at > now
            ]
            delay = self.s.refresh_s
            if deadlines:
                delay = min(delay, min(deadlines) - now)
            self._stop.wait(delay)

    def health(self) -> dict:
        st = self.collector.snapshot()
        sl = self.serial
        return {
            "ok": True,
            "uptime_s": int(time.time() - self.started),
            "refreshed_at": st.refreshed_at,
            "source_errors": st.errors,
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
                    self._send(200, build_status(app.collector.snapshot(), time.time()))
                elif path == "/healthz":
                    self._send(200, app.health())
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                url = urlparse(self.path)
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

        self.collector.refresh()
        threading.Thread(target=self.refresh_loop, name="refresh", daemon=True).start()
        if self.serial:
            threading.Thread(target=self.serial.run, name="serial", daemon=True).start()
        httpd = ThreadingHTTPServer((self.s.bind_host, self.s.bind_port), Handler)
        log.event("service.started", bind=f"{self.s.bind_host}:{self.s.bind_port}", serial=self.s.serial_port if self.serial else "off")
        try:
            httpd.serve_forever(poll_interval=0.5)
        finally:
            self._stop.set()
            if self.serial:
                self.serial.stop()
            httpd.server_close()
            log.event("service.stopped")
