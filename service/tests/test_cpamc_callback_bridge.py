import http.client
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cpamc_callback_bridge as bridge  # noqa: E402

SECRET = "code=SECRETCODE&state=abc%2Fdef"


def _serve(srv):
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return t


class FakeUpstream(ThreadingHTTPServer):
    def __init__(self, status=200, location=None):
        self.hits = []
        self.status = status
        self.location = location
        super().__init__(("127.0.0.1", 0), _UpHandler)


class _UpHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.server.hits.append((self.path, dict(self.headers)))
        self.send_response(self.server.status)
        if self.server.location:
            self.send_header("Location", self.server.location)
        body = b"UPSTREAM-BODY-SECRET"
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = bridge.make_server(0)
        self.up = FakeUpstream()
        self.base = f"http://127.0.0.1:{self.up.server_address[1]}"
        self._patch = patch.object(bridge, "load_base", lambda: self.base)
        self._patch.start()
        self.servers = [self.bridge, self.up]
        for s in self.servers:
            _serve(s)

    def tearDown(self):
        self._patch.stop()
        for s in self.servers:
            s.shutdown()
            s.server_close()

    def req(self, method, target, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.bridge.bridge_port, timeout=10)
        c.request(method, target, headers=headers or {})
        r = c.getresponse()
        body = r.read()
        c.close()
        return r.status, body

    def test_binds_loopback_only(self):
        self.assertEqual(self.bridge.server_address[0], "127.0.0.1")

    def test_forwards_exact_query_without_headers(self):
        for path in ("/anthropic/callback", "/codex/callback"):
            status, body = self.req(
                "GET", f"{path}?{SECRET}", {"Cookie": "c=1", "Authorization": "Bearer x"}
            )
            self.assertEqual(status, 200)
            self.assertNotIn(b"UPSTREAM-BODY", body)
            self.assertNotIn(b"SECRETCODE", body)
            target, hdrs = self.up.hits[-1]
            self.assertEqual(target, f"{path}?{SECRET}")
            low = {k.lower() for k in hdrs}
            self.assertFalse({"cookie", "authorization"} & low)

    def test_health_is_static(self):
        status, body = self.req("GET", "/_bridge/health")
        self.assertEqual(status, 200)
        self.assertIn(b'"ok": true', body)
        self.assertEqual(self.up.hits, [])

    def test_health_warns_when_upstream_configuration_is_invalid(self):
        with patch.object(bridge, 'load_base', return_value='http://localhost:' + str(self.bridge.bridge_port)):
            status, body = self.req('GET', '/_bridge/health')
        self.assertEqual(status, 503)
        self.assertIn(b'"ok":false', body)
        self.assertEqual(self.up.hits, [])

    def test_other_paths_404(self):
        for p in ("/", "/v0/management/auth-files", "/anthropic/callback/x",
                  "//evil/anthropic/callback", "/anthropic%2Fcallback",
                  "/%61nthropic/callback", "/anthropic/callback/", "/_bridge/health?x=1"):
            status, _ = self.req("GET", p)
            self.assertEqual(status, 404, p)
        self.assertEqual(self.up.hits, [])

    def test_non_get_rejected(self):
        for m in ("POST", "PUT", "DELETE"):
            status, _ = self.req(m, "/anthropic/callback?" + SECRET)
            self.assertEqual(status, 405, m)
        self.assertEqual(self.up.hits, [])

    def test_oversized_target(self):
        status, _ = self.req("GET", "/anthropic/callback?" + "a" * 17000)
        self.assertIn(status, (404, 414))
        self.assertEqual(self.up.hits, [])

    def test_bad_bases_502(self):
        port = self.bridge.bridge_port
        bad = [
            f"http://127.0.0.1:{port}", f"http://localhost:{port}", f"http://[::1]:{port}",
            "ftp://host", "not a url", "http://u:p@host:1", "http://host:1?x=1",
            "http://host:1#f", "http://host:1/sub", "http://host:notaport", "",
        ]
        for b in bad:
            with patch.object(bridge, "load_base", lambda b=b: b):
                status, body = self.req("GET", "/codex/callback?" + SECRET)
            self.assertEqual(status, 502, b)
            self.assertNotIn(b"SECRETCODE", body)
        self.assertEqual(self.up.hits, [])

    def test_redirect_not_followed(self):
        other = FakeUpstream()
        _serve(other)
        self.servers.append(other)
        self.up.status = 302
        self.up.location = f"http://127.0.0.1:{other.server_address[1]}/stolen"
        status, body = self.req("GET", "/anthropic/callback?" + SECRET)
        self.assertEqual(status, 502)
        self.assertEqual(len(self.up.hits), 1)
        self.assertEqual(other.hits, [])

    def test_upstream_error_status_502(self):
        self.up.status = 500
        status, body = self.req("GET", "/codex/callback?" + SECRET)
        self.assertEqual(status, 502)
        self.assertNotIn(b"UPSTREAM-BODY", body)

    def test_upstream_down_502(self):
        self.up.shutdown()
        self.up.server_close()
        self.servers.remove(self.up)
        status, _ = self.req("GET", "/codex/callback?" + SECRET)
        self.assertEqual(status, 502)


if __name__ == "__main__":
    unittest.main()
