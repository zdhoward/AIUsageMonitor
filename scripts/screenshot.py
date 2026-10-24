"""Capture the display's frame buffer over USB serial and save it as a PNG.

Usage: python scripts/screenshot.py [--port COM6] [--rot N] [--out shot.png] [--feed]

--rot N   apply rotation N on the device first (until reboot; test only)
--feed    send the current aimon payload (from http://127.0.0.1:8797/v1/device) first
--payload FILE   send this JSON payload first (test fixtures, e.g. reset credits)
If the aimon service is running, it is asked to release the port and resumes afterwards.
Requires pyserial. The PNG is written with the stdlib (zlib).
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
import urllib.request
import zlib
from pathlib import Path

import serial
from serial.tools import list_ports

API = "http://127.0.0.1:8797"


def api(method: str, path: str):
    req = urllib.request.Request(API + path, method=method)
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.load(r)


def find_port() -> str:
    for p in list_ports.comports():
        if (p.vid, p.pid) == (0x1A86, 0x7523):
            return p.device
    sys.exit("no CH340 port found")


def write_png(path: Path, w: int, h: int, rgb332: bytes, scale: int) -> None:
    rows = []
    for y in range(h):
        row = bytearray()
        for v in rgb332[y * w:(y + 1) * w]:
            px = bytes(((v & 0xE0) | (v & 0xE0) >> 3 | (v & 0xE0) >> 6,
                        ((v & 0x1C) << 3) | (v & 0x1C) | (v & 0x1C) >> 3,
                        (v & 0x03) * 0x55))
            row += px * scale
        line = b"\x00" + bytes(row)
        rows.extend([line] * scale)
    raw = b"".join(rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * scale, h * scale, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def read_line(s: serial.Serial, deadline: float) -> bytes:
    buf = b""
    while time.time() < deadline:
        c = s.read(1)
        if c == b"\n":
            return buf
        buf += c
    raise TimeoutError("device did not answer")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--rot", type=int)
    ap.add_argument("--out", default="shot.png")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--feed", action="store_true")
    ap.add_argument("--payload", help="JSON file to send before capturing")
    ap.add_argument("--next", type=int, default=0, help="advance this many views before capturing")
    ap.add_argument("--wait", type=float, default=0, help="seconds to wait after feeding (max 40)")
    args = ap.parse_args()

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8")) if args.payload else None
    if args.feed and payload is None:
        payload = api("GET", "/v1/device")
    paused = False
    try:
        api("POST", "/v1/serial/pause?seconds=90")
        paused = True
        time.sleep(0.8)
    except OSError:
        pass

    s = serial.Serial()
    s.port, s.baudrate, s.timeout = args.port or find_port(), 115200, 0.5
    s.dtr = s.rts = False
    s.open()
    try:
        if args.rot is not None:
            s.write(f"!ROT {args.rot}\n".encode())
            time.sleep(0.5)
        if payload:
            s.write((json.dumps(payload, separators=(",", ":")) + "\n").encode())
            time.sleep(0.5)
        for _ in range(args.next):
            s.write(b"!NEXT\n")
            time.sleep(0.1)
        time.sleep(max(0, min(args.wait, 40)))
        s.reset_input_buffer()
        s.write(b"!SHOT\n")
        deadline = time.time() + 30
        while True:
            line = read_line(s, deadline)
            if line.startswith(b"@SHOT "):
                _, w, h, _bpp = line.decode().split()
                w, h = int(w), int(h)
                break
        data = b""
        while len(data) < w * h and time.time() < deadline:
            data += s.read(w * h - len(data))
        if len(data) < w * h:
            raise TimeoutError(f"short frame: {len(data)}/{w * h}")
    finally:
        s.close()
        if paused:
            try:
                api("POST", "/v1/serial/resume")
            except OSError:
                pass
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_png(Path(args.out), w, h, data, args.scale)
    print(f"saved {args.out} ({w}x{h})")


if __name__ == "__main__":
    main()
