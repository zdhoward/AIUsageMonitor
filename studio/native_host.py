"""Native preview host and live device link for Scene Studio.

NativeHost wraps scenehost.dll (the firmware scene engine built for Windows):
previews are the device's own pixels, and unsaved edits travel as tune blobs
(firmware/AIUsageMonitor/tune.h). LiveLink keeps the display's serial port
open while live editing so each edit reaches the device in well under a second.
"""
from __future__ import annotations

import ctypes
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(__file__).with_name("native") / "build"
W, H = 320, 240


class NativeHost:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.dll = None
        self.ids: list[str] = []
        self.path = None
        self.blobs: dict[str, bytes] = {}
        self.building = False
        self.last_error = ""
        self.load()

    def load(self) -> bool:
        dlls = sorted(BUILD.glob("scenehost-*.dll"))
        if not dlls:
            return False
        dll = ctypes.CDLL(str(dlls[-1]))
        dll.sh_id.restype = ctypes.c_char_p
        dll.sh_render.argtypes = [ctypes.c_int, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int,
                                  ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        with self.lock:
            self.dll, self.path = dll, dlls[-1]
            self.ids = [dll.sh_id(i).decode() for i in range(dll.sh_count())]
            self.blobs.clear()
        return True

    def stale(self) -> bool:
        """True when the library or engine sources are newer than the DLL."""
        if not self.path:
            return True
        built = self.path.stat().st_mtime
        sources = list((ROOT / "assets" / "library").glob("*/entry.json")) + list((ROOT / "assets" / "themes").glob("*.json"))
        sources += [ROOT / "firmware" / "AIUsageMonitor" / f for f in ("scene.cpp", "scene.h", "anim.cpp", "tune.cpp")]
        return any(p.stat().st_mtime > built for p in sources if p.exists())

    def rebuild(self, profile: str | None = None) -> None:
        """Regenerate scenes_gen and rebuild the DLL (background thread)."""
        if self.building:
            return

        def work():
            self.building = True
            try:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                cmd = [sys.executable, "scripts/asset_convert.py"] + (["--profile", profile] if profile else [])
                subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, creationflags=flags)
                subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                str(Path(__file__).with_name("native") / "build.ps1")],
                               cwd=ROOT, check=True, capture_output=True, creationflags=flags)
                self.load()
                self.last_error = ""
            except subprocess.CalledProcessError as e:
                self.last_error = (e.stderr or e.stdout or b"").decode(errors="replace")[-600:]
            finally:
                self.building = False
        threading.Thread(target=work, daemon=True).start()

    def index(self, scene_id: str) -> int:
        return self.ids.index(scene_id) if scene_id in self.ids else -1

    def blob(self, entry_id: str, scene: dict, shift: bool = False) -> bytes:
        import scenes  # scripts/ is on sys.path (server.py)
        key = f"{entry_id}{shift}" + json.dumps(scene, sort_keys=True)
        if key not in self.blobs:
            if len(self.blobs) > 64:
                self.blobs.clear()
            target = entry_id + scenes.SHIFT_SUFFIX if shift else entry_id
            self.blobs[key] = scenes.tune_blob(entry_id, scene, self.index(target), shift)
        return self.blobs[key]

    def render(self, entry_id: str, t: int, scene: dict | None, warm: int = 0,
               shift: bool = False) -> tuple[bytes, str]:
        """RGB332 frame for an entry or its theme shift (optionally with unsaved edits)."""
        import scenes
        i = self.index(entry_id + scenes.SHIFT_SUFFIX if shift else entry_id)
        if not self.dll or i < 0:
            raise LookupError("not in the preview engine yet")
        status = "ok"
        blob = b""
        if scene is not None:
            try:
                blob = self.blob(entry_id, scene, shift)
            except (ValueError, OSError, KeyError) as e:
                status = f"untuned: {e}"
        buf = (ctypes.c_ubyte * (W * H))()
        with self.lock:
            for k in range(warm, -1, -1):  # warm-up frames settle stateful generators
                rc = self.dll.sh_render(i, max(0, t - k * 40), blob, len(blob), buf, W, H)
            if rc == -1:
                status = "untuned: layers changed, rebuilding"
        return bytes(buf), status


class LiveLink:
    """Holds the display's serial port while live editing; latest edit wins."""

    def __init__(self, open_port, pause, resume) -> None:
        self.open_port, self.pause, self.resume = open_port, pause, resume
        self.port = None
        self.lock = threading.Lock()
        self.pending: str | None = None
        self.last_use = 0.0
        self.last_reply = ""
        self.wake = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def send(self, line: str) -> None:
        self.pending = line
        self.wake.set()

    def close(self, untune: bool = True) -> None:
        """Release the port; untune=False keeps the edit on screen (e.g. for a capture)."""
        with self.lock:
            if self.port:
                try:
                    if untune:
                        self.port.write(b"!TUNE off\n")
                    self.port.close()
                finally:
                    self.port = None
                    self.resume()

    def _run(self) -> None:
        while True:
            self.wake.wait(5)
            self.wake.clear()
            line, self.pending = self.pending, None
            with self.lock:
                if line:
                    try:
                        if not self.port:
                            self.pause(600)
                            self.port = self.open_port()
                        self.port.reset_input_buffer()
                        self.port.write((line + "\n").encode())
                        end = time.time() + 1.5
                        while time.time() < end:
                            reply = self.port.readline().decode(errors="ignore").strip()
                            if reply.startswith(("@TUNE", "@ERR tune")):
                                self.last_reply = reply
                                break
                        self.last_use = time.time()
                    except Exception as e:  # unplugged, port busy...
                        self.last_reply = f"@ERR {e}"
                        self.port = None
                        self.resume()
            if self.port and time.time() - self.last_use > 45:  # idle: give the port back
                self.close()
