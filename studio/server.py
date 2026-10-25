"""Scene Studio: a local web app for profiles, the scene library and the device.

Run: python -m studio   (opens an app window at http://127.0.0.1:8798)
Standard library only, plus pyserial for the device panel.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import profile_gen  # noqa: E402
import scenes  # noqa: E402
from studio.native_host import LiveLink, NativeHost  # noqa: E402

WEB = Path(__file__).with_name("web")
LIBRARY = ROOT / "assets" / "library"
PROFILES = profile_gen.PROFILES
AIMON = "http://127.0.0.1:8797"
PORT = 8798
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")

jobs: dict[str, dict] = {}
serial_lock = threading.Lock()
last_shot: dict = {}


# ----------------------------------------------------------------- device
def _pause_service(seconds: int) -> None:
    try:
        req = urllib.request.Request(f"{AIMON}/v1/serial/pause?seconds={seconds}", method="POST")
        urllib.request.urlopen(req, timeout=3)
        time.sleep(0.8)
    except OSError:
        pass  # service not running: the port is already free


def _resume_service() -> None:
    try:
        urllib.request.urlopen(urllib.request.Request(f"{AIMON}/v1/serial/resume", method="POST"), timeout=3)
    except OSError:
        pass


def _open_port():
    import serial
    from serial.tools import list_ports
    port = next((p.device for p in list_ports.comports() if (p.vid, p.pid) == (0x1A86, 0x7523)), None)
    if not port:
        raise RuntimeError("Display not found. Is it plugged in?")
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, 115200, 0.5
    s.dtr = s.rts = False
    s.open()
    return s


def device(commands: list[str], shot: bool) -> dict:
    """Send commands, collect '@' replies, optionally capture the framebuffer."""
    live.close(untune=False)  # a live-edit session holds the port; hand it over
    with serial_lock:
        _pause_service(60)
        try:
            s = _open_port()
            replies = []
            try:
                for c in commands:
                    s.reset_input_buffer()
                    s.write((c + "\n").encode())
                    end = time.time() + 1.0
                    while time.time() < end:
                        line = s.readline().decode(errors="ignore").strip()
                        if line.startswith("@"):
                            replies.append(line)
                            break
                result = {"replies": replies}
                if shot:
                    s.reset_input_buffer()
                    s.write(b"!SHOT\n")
                    end = time.time() + 30
                    while time.time() < end:
                        line = s.readline()
                        if line.startswith(b"@SHOT "):
                            break
                        if line.startswith(b"@ERR no framebuffer"):  # other @ERR lines belong to the usage feed
                            raise RuntimeError(line.decode().strip())
                    else:
                        raise RuntimeError("no frame from the display")
                    _, w, h, _ = line.decode().split()
                    w, h = int(w), int(h)
                    data = b""
                    while len(data) < w * h and time.time() < end:
                        data += s.read(w * h - len(data))
                    if len(data) < w * h:
                        raise RuntimeError("frame transfer was cut short")
                    png = rgb332_png(w, h, data)
                    last_shot.update(png=png, at=datetime.now().isoformat(timespec="seconds"))
                    result["shot"] = "data:image/png;base64," + base64.b64encode(png).decode()
                return result
            finally:
                s.close()
        finally:
            _resume_service()


def rgb332_png(w: int, h: int, px: bytes) -> bytes:
    import struct
    import zlib
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for c in px[y * w:(y + 1) * w]:
            raw += bytes((((c >> 5) & 7) * 255 // 7, ((c >> 2) & 7) * 255 // 7, (c & 3) * 85))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


native = NativeHost()
live = LiveLink(_open_port, _pause_service, _resume_service)


# ------------------------------------------------------------------- jobs
def run_job(kind: str, profile: str) -> str:
    jid = uuid.uuid4().hex[:8]
    job = jobs[jid] = {"id": jid, "kind": kind, "state": "running", "log": "", "step": ""}

    def step(name: str, args: list[str]) -> bool:
        job["step"] = name
        proc = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for line in proc.stdout:
            job["log"] += line
        return proc.wait() == 0

    def work():
        ps = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
        ok = step("Converting art", [sys.executable, "scripts/asset_convert.py", "--profile", profile])
        ok = ok and step("Building firmware", ps + ["scripts/build.ps1", "-Profile", profile])
        if ok:
            native.rebuild(profile)
        if ok and kind == "flash":
            with serial_lock:
                ok = step("Flashing display", ps + ["scripts/flash.ps1"])
        job["state"] = "done" if ok else "failed"
        m = re.search(r"Sketch uses (\d+) bytes \((\d+)%\)", job["log"])
        if m:
            job["size"] = {"bytes": int(m.group(1)), "percent": int(m.group(2))}
    threading.Thread(target=work, daemon=True).start()
    return jid


# ---------------------------------------------------------------- library
def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def library() -> list[dict]:
    items = []
    for d in sorted(LIBRARY.glob("*/entry.json")):
        e = json.loads(d.read_text(encoding="utf-8"))
        e["id"] = d.parent.name
        e["preview_url"] = f"/library/{d.parent.name}/{e.get('preview', 'preview.png')}"
        e["has_preview"] = (d.parent / e.get("preview", "preview.png")).is_file()
        items.append(e)
    return sorted(items, key=lambda e: e.get("created", ""), reverse=True)


def save_to_library(body: dict) -> dict:
    name = body.get("name", "").strip()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    if not name or not SLUG.match(slug):
        raise ValueError("Give it a name first")
    if not last_shot:
        raise ValueError("Capture the screen first")
    d = LIBRARY / slug
    if d.exists():
        slug = f"{slug}-{datetime.now():%m%d%H%M}"
        d = LIBRARY / slug
    d.mkdir(parents=True)
    (d / "preview.png").write_bytes(last_shot["png"])
    entry = {"name": name, "kind": body.get("kind", "capture"), "notes": body.get("notes", ""),
             "created": datetime.now().isoformat(timespec="seconds"), "commit": git_commit(),
             "profile": body.get("profile", ""), "preview": "preview.png"}
    (d / "entry.json").write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    return entry


IMPORTABLE = {".png", ".gif", ".aseprite", ".ase", ".jpg", ".jpeg"}
LOSPEC = "https://lospec.com/palette-list"
THEMES_DIR = ROOT / "assets" / "themes"
HEX = re.compile(r"^[0-9a-fA-F]{6}$")


def lospec_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AIUsageMonitor-SceneStudio/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def lospec_search(tag: str, page: int) -> list[dict]:
    tag = re.sub(r"[^a-z0-9-]", "", tag.lower())
    url = f"{LOSPEC}/load?colorNumberFilterType=any&page={max(0, page)}&tag={tag}&sortingType=default"
    data = lospec_get(url)
    return [{"slug": p["slug"], "title": p.get("title", p["slug"]), "colors": p.get("colors", [])[:32],
             "author": (p.get("user") or {}).get("name", ""), "likes": p.get("likes", 0)}
            for p in data.get("palettes", []) if p.get("slug")]


def import_palette(body: dict) -> dict:
    """Save a Lospec palette (slug or URL) as a theme in assets/themes/."""
    slug = body.get("slug", "").strip().rstrip("/").split("/")[-1].removesuffix(".json").lower()
    if not SLUG.match(slug):
        raise ValueError("Paste a Lospec palette name or link")
    try:
        d = lospec_get(f"{LOSPEC}/{slug}.json")
    except OSError as e:
        raise ValueError(f"Lospec did not return '{slug}': {e}") from e
    colors = [c for c in d.get("colors", []) if HEX.match(c)]
    if len(colors) < 2:
        raise ValueError(f"'{slug}' has no usable colours")
    if slug in scenes.THEMES:
        raise ValueError(f"'{slug}' clashes with a built-in theme")
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"name": d.get("name", slug), "author": d.get("author", ""), "url": f"{LOSPEC}/{slug}",
             "source": "lospec", "colors": colors}
    (THEMES_DIR / f"{slug}.json").write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    return {"id": slug, **entry}


def import_files(body: dict) -> dict:
    """Create a scene entry from dropped files (ordered back to front)."""
    name = body.get("name", "").strip()
    files = body.get("files", [])
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    if not name or not SLUG.match(slug):
        raise ValueError("Give the import a name")
    if not files:
        raise ValueError("Drop at least one image")
    d = LIBRARY / slug
    if d.exists():
        slug = f"{slug}-{datetime.now():%m%d%H%M}"
        d = LIBRARY / slug
    (d / "src").mkdir(parents=True)
    saved = []
    for f in files:
        fname = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(f["name"]).name)
        if Path(fname).suffix.lower() not in IMPORTABLE:
            shutil.rmtree(d)
            raise ValueError(f"{f['name']}: use PNG, GIF, JPG or Aseprite files")
        (d / "src" / fname).write_bytes(base64.b64decode(f["data"].split(",")[-1]))
        saved.append(f"src/{fname}")
    try:
        scene = scenes.auto_scene(d, saved)
        entry = {"name": name, "kind": "scene", "notes": body.get("notes", ""),
                 "created": datetime.now().isoformat(timespec="seconds"), "commit": git_commit(),
                 "profile": "", "preview": "preview.png", "license": body.get("license", ""), "scene": scene}
        (d / "entry.json").write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
        scenes.prepare_with_still(slug)
        native.rebuild()
    except Exception as ex:  # unreadable art: leave nothing half-imported behind
        shutil.rmtree(d, ignore_errors=True)
        raise ValueError(f"Could not import: {ex}") from ex
    return {"id": slug}


# ------------------------------------------------------------------- http
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def log_message(self, *_):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # always serve the current UI and previews
        super().end_headers()

    def send_json(self, obj, status=200):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            profiles = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(PROFILES.glob("*.json"))}
            return self.send_json({"profiles": profiles, "library": library(), "commit": git_commit(),
                                   "scenes": scenes.scene_list(), "native": native.ids,
                                   "native_building": native.building})
        if path == "/api/native":
            return self.send_json({"ids": native.ids, "building": native.building, "error": native.last_error,
                                   "live": live.last_reply})
        if path == "/api/themes":
            return self.send_json({t: scenes.lut(t) for t in scenes.theme_names()})
        if path == "/api/theme-info":
            return self.send_json(scenes.theme_info())
        if path == "/api/lospec":
            q = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            return self.send_json(lospec_search(q.get("tag", [""])[0], int(q.get("page", ["0"])[0] or 0)))
        if path.startswith("/api/jobs/"):
            job = jobs.get(path.rsplit("/", 1)[1])
            return self.send_json(job or {"error": "unknown job"}, 200 if job else 404)
        for prefix, base in (("/library/", LIBRARY), ("/docimg/", ROOT / "docs" / "img")):
            if not path.startswith(prefix):
                continue
            f = (base / urllib.parse.unquote(path[len(prefix):])).resolve()
            if base.resolve() in f.parents and f.is_file():
                data = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png" if f.suffix == ".png" else "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                return self.wfile.write(data)
            return self.send_error(HTTPStatus.NOT_FOUND)
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            b = self.body()
            if path.startswith("/api/profiles/"):
                pid = path.rsplit("/", 1)[1]
                if not SLUG.match(pid):
                    raise ValueError("Profile names use lowercase letters, numbers and dashes")
                errs = profile_gen.validate({**b, "id": pid})
                if errs:
                    raise ValueError("; ".join(errs))
                (PROFILES / f"{pid}.json").write_text(json.dumps(b, indent=2) + "\n", encoding="utf-8")
                return self.send_json({"ok": True})
            if path in ("/api/build", "/api/flash"):
                return self.send_json({"job": run_job(path[5:], b["profile"])})
            if path == "/api/device":
                cmds = [c for c in b.get("commands", []) if re.fullmatch(r"![A-Z]+( [a-z0-9-]{1,48})?", c)]
                return self.send_json(device(cmds, bool(b.get("shot"))))
            if path == "/api/library":
                return self.send_json(save_to_library(b))
            m = re.fullmatch(r"/api/library/([a-z0-9-]+)/preview", path)
            if m and (LIBRARY / m.group(1) / "entry.json").is_file():
                png = base64.b64decode(b["data"].split(",")[-1])
                if not png.startswith(b"\x89PNG"):
                    raise ValueError("preview must be a PNG")
                (LIBRARY / m.group(1) / "preview.png").write_bytes(png)
                return self.send_json({"ok": True})
            if path == "/api/frame":
                try:
                    frame, status = native.render(b["entry"], int(b.get("t", 0)), b.get("scene"), int(b.get("warm", 0)))
                except LookupError as e:
                    return self.send_json({"error": str(e)}, 404)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("X-Tune", status)
                self.send_header("Content-Length", str(len(frame)))
                self.end_headers()
                return self.wfile.write(frame)
            if path == "/api/live":
                if b.get("off"):
                    live.close()
                    return self.send_json({"ok": True})
                blob = native.blob(b["entry"], b["scene"]) if native.index(b["entry"]) >= 0 else \
                    scenes.tune_blob(b["entry"], b["scene"], [s["id"] for s in scenes.scene_list()].index(b["entry"]))
                live.send("!TUNE " + blob.hex())
                return self.send_json({"ok": True, "bytes": len(blob), "last": live.last_reply})
            if path == "/api/native/rebuild":
                native.rebuild(b.get("profile"))
                return self.send_json({"ok": True})
            if path == "/api/themes/lospec":
                return self.send_json(import_palette(b))
            m = re.fullmatch(r"/api/themes/([a-z0-9-]+)/delete", path)
            if m and (THEMES_DIR / f"{m.group(1)}.json").is_file():
                (THEMES_DIR / f"{m.group(1)}.json").unlink()
                return self.send_json({"ok": True})
            if path == "/api/import":
                return self.send_json(import_files(b))
            m = re.fullmatch(r"/api/library/([a-z0-9-]+)/scene", path)
            if m and (LIBRARY / m.group(1) / "entry.json").is_file():
                f = LIBRARY / m.group(1) / "entry.json"
                e = json.loads(f.read_text(encoding="utf-8"))
                e["scene"] = b["scene"]
                if "name" in b:
                    e["name"] = b["name"]
                f.write_text(json.dumps(e, indent=2) + "\n", encoding="utf-8")
                scenes.prepare_with_still(m.group(1))
                if native.stale():
                    native.rebuild()
                return self.send_json({"ok": True, "rebuilding": native.building})
            if path.startswith("/api/library/") and path.endswith("/delete"):
                lid = path.split("/")[3]
                if SLUG.match(lid) and (LIBRARY / lid).is_dir():
                    shutil.rmtree(LIBRARY / lid)
                return self.send_json({"ok": True})
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, RuntimeError, KeyError, OSError) as e:
            self.send_json({"error": str(e)}, 400)
        except Exception as e:  # never answer with a bare 500 page the UI cannot read
            log_error(f"POST {path}")
            self.send_json({"error": f"{type(e).__name__}: {e} (details in logs/studio.log)"}, 500)


LOG = ROOT / "logs" / "studio.log"


def log_error(context: str) -> None:
    import traceback
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {context}\n{traceback.format_exc()}\n")


def open_window(url: str) -> None:
    edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    try:
        subprocess.Popen([edge, f"--app={url}", "--window-size=1280,860"])
    except OSError:
        import webbrowser
        webbrowser.open(url)


def main() -> None:
    LIBRARY.mkdir(parents=True, exist_ok=True)
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else PORT
    url = f"http://127.0.0.1:{port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        # A Studio is already running: open a window onto it instead of failing silently.
        if "--no-window" not in sys.argv:
            open_window(url)
        return
    print(f"Scene Studio on {url}  (Ctrl+C to quit)")
    if native.stale():
        native.rebuild()
    if "--no-window" not in sys.argv:
        open_window(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
