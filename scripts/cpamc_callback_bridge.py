"""Loopback bridge for CPAMC OAuth callbacks.

CPAMC hands the browser http://127.0.0.1:8317/{anthropic,codex}/callback while the
CPAMC host itself listens on another (Tailscale) address. This bridge listens on
127.0.0.1 only and replays the final GET hop to the configured CPAMC base.

Safety: only two fixed GET paths plus a static health check; the query is forwarded
byte for byte but never logged or echoed; no request headers are forwarded; proxies
and redirects are disabled; the upstream body is discarded in favour of a fixed page.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))
from aimon.sources.cpamc import load_base  # noqa: E402

BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8317
CALLBACK_PATHS = frozenset({"/anthropic/callback", "/codex/callback"})
HEALTH_PATH = "/_bridge/health"
MAX_TARGET = 16 * 1024
MAX_UPSTREAM_READ = 64 * 1024
UPSTREAM_TIMEOUT_S = 8
LOOPBACK_NAMES = frozenset({"127.0.0.1", "localhost", "::1"})

SUCCESS_HTML = (
    b"<!doctype html><meta charset=utf-8><title>Callback delivered</title>"
    b"<p>Login callback delivered. You can close this tab.</p>"
)
FAIL_HTML = (
    b"<!doctype html><meta charset=utf-8><title>Callback failed</title>"
    b"<p>Callback could not be delivered. Restart the login.</p>"
)
HEALTH_JSON = json.dumps({"ok": True, "service": "cpamc-callback-bridge"}).encode()


class UpstreamError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # 3xx surfaces as HTTPError
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def validate_base(base: str, bridge_port: int) -> str:
    """Return a safe upstream base (no trailing slash) or raise UpstreamError."""
    try:
        parts = urlsplit(base)
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise UpstreamError("malformed base") from None
    if parts.scheme not in ("http", "https") or not host:
        raise UpstreamError("bad scheme/host")
    if parts.username is not None or parts.password is not None:
        raise UpstreamError("credentials in base")
    if parts.query or parts.fragment or "?" in base or "#" in base:
        raise UpstreamError("query/fragment in base")
    if parts.path.strip("/"):
        raise UpstreamError("path in base")
    eff_port = port or (443 if parts.scheme == "https" else 80)
    if host.lower() in LOOPBACK_NAMES and eff_port == bridge_port:
        raise UpstreamError("self loop")
    return f"{parts.scheme}://{parts.netloc}"


def split_target(target: str):
    """Return (path, raw_query) for an acceptable request target, else None."""
    if len(target) > MAX_TARGET:
        return None
    if not all(0x21 <= ord(c) <= 0x7E for c in target) or "#" in target or "\\" in target:
        return None
    path, sep, query = target.partition("?")
    if not path.startswith("/") or path.startswith("//") or "%" in path:
        return None
    return path, (query if sep else None)


def forward(upstream_base: str, path: str, query) -> bool:
    url = upstream_base + path + (("?" + query) if query is not None else "")
    req = urllib.request.Request(
        url, method="GET", headers={"User-Agent": "cpamc-callback-bridge"}
    )
    try:
        with _OPENER.open(req, timeout=UPSTREAM_TIMEOUT_S) as resp:
            status = resp.status
            resp.read(MAX_UPSTREAM_READ)
    except (urllib.error.URLError, OSError, ValueError):
        return False
    return status == 200


class Handler(BaseHTTPRequestHandler):
    server_version = "cpamc-callback-bridge"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):  # never log targets: they carry OAuth codes
        pass

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if len(self.path) > MAX_TARGET:
            return self._send(414, FAIL_HTML, "text/html; charset=utf-8")
        parsed = split_target(self.path)
        if parsed is None:
            return self._send(404, b"not found", "text/plain")
        path, query = parsed
        if path == HEALTH_PATH and query is None:
            try:
                validate_base(load_base(), self.server.bridge_port)
            except Exception:
                return self._send(503, b'{"ok":false,"configured":false}', "application/json")
            return self._send(200, HEALTH_JSON, "application/json")
        if path not in CALLBACK_PATHS:
            return self._send(404, b"not found", "text/plain")
        try:
            base = validate_base(load_base(), self.server.bridge_port)
        except Exception:
            return self._send(502, FAIL_HTML, "text/html; charset=utf-8")
        if forward(base, path, query):
            return self._send(200, SUCCESS_HTML, "text/html; charset=utf-8")
        self._send(502, FAIL_HTML, "text/html; charset=utf-8")

    def _reject(self) -> None:
        self._send(405, b"method not allowed", "text/plain")

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = _reject


class _BridgeHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"


def make_server(port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    srv = _BridgeHTTPServer((BIND_HOST, port), Handler)
    srv.daemon_threads = True
    srv.bridge_port = srv.server_address[1]
    return srv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args(argv)
    srv = make_server(args.port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
