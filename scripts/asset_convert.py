"""Convert images and animations into compiled firmware assets.

Reads assets/manifest.json and writes firmware/AIUsageMonitor/assets_gen.{h,cpp}.
Sources: .gif (all frames, per-frame delays), .png/.jpg (one frame) and
.aseprite/.ase (exported with the Aseprite CLI; optional single layer, tags kept).
Frames are trimmed to their shared opaque bounds, snapped to RGB332 and
run-length encoded. Alpha < 128 is transparent.

Manifest entry fields:
  name   C identifier (asset becomes ASSET_<name>)
  src    path relative to assets/
  layer  optional Aseprite layer to export alone
  mode   "frames" (default) or "rects": emit the bounding box and colour of each
         connected blob in frame 0, for code-driven effects such as window blinks.
  max_bytes  optional budget; conversion fails if the encoded asset is larger.

Usage: python scripts/asset_convert.py [--check]
Set ASEPRITE to the executable if it is not in the default Steam location.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FW = ROOT / "firmware" / "AIUsageMonitor"
STEAM = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe")


def aseprite_exe() -> str:
    exe = os.environ.get("ASEPRITE") or shutil.which("aseprite") or (str(STEAM) if STEAM.exists() else None)
    if not exe:
        sys.exit("Aseprite not found; set ASEPRITE to its executable")
    return exe


def rgb332(r: int, g: int, b: int) -> int:
    return (round(r * 7 / 255) << 5) | (round(g * 7 / 255) << 2) | round(b * 3 / 255)


def load_gif(path: Path):
    frames, durations = [], []
    with Image.open(path) as im:
        for f in ImageSequence.Iterator(im):
            frames.append(f.convert("RGBA"))
            durations.append(int(f.info.get("duration", 100)) or 100)
    return frames, durations, []


def load_aseprite(path: Path, layer: str | None):
    with tempfile.TemporaryDirectory() as t:
        sheet, data = Path(t) / "sheet.png", Path(t) / "sheet.json"
        cmd = [aseprite_exe(), "-b"]
        if layer:
            cmd += ["--layer", layer]
        cmd += [str(path), "--sheet", str(sheet), "--sheet-type", "horizontal",
                "--data", str(data), "--format", "json-array", "--list-tags"]
        subprocess.run(cmd, check=True, capture_output=True)
        meta = json.loads(data.read_text())
        with Image.open(sheet) as im:
            im = im.convert("RGBA")
            frames = []
            for f in meta["frames"]:
                r = f["frame"]
                frames.append(im.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])))
    durations = [f["duration"] for f in meta["frames"]]
    tags = [(t["name"], t["from"], t["to"]) for t in meta["meta"].get("frameTags", [])]
    return frames, durations, tags


def load(entry: dict):
    path = ASSETS / entry["src"]
    ext = path.suffix.lower()
    if ext == ".gif":
        return load_gif(path)
    if ext in (".aseprite", ".ase"):
        return load_aseprite(path, entry.get("layer"))
    with Image.open(path) as im:
        return [im.convert("RGBA")], [1000], []


def to_pixels(im: Image.Image) -> list:
    return [rgb332(r, g, b) if a >= 128 else None for r, g, b, a in im.getdata()]


def rle(px: list) -> bytes:
    """0x00-0x3F literal n+1 bytes; 0x40-0x7F repeat n+1 of next byte; 0x80-0xFF skip n+1."""
    out, i, n = bytearray(), 0, len(px)
    while i < n:
        if px[i] is None:
            j = i
            while j < n and px[j] is None and j - i < 128:
                j += 1
            out.append(0x80 | (j - i - 1))
            i = j
            continue
        j = i
        while j < n and px[j] == px[i] and j - i < 64:
            j += 1
        if j - i >= 3:
            out += bytes((0x40 | (j - i - 1), px[i]))
            i = j
            continue
        j = i
        while j < n and px[j] is not None and j - i < 64:
            if j + 2 < n and px[j] == px[j + 1] == px[j + 2]:
                break
            j += 1
        j = max(j, i + 1)
        out.append(j - i - 1)
        out += bytes(px[i:j])
        i = j
    return bytes(out)


def rects(im: Image.Image) -> list:
    w, h = im.size
    px = to_pixels(im)
    seen = bytearray(w * h)
    found = []
    for start in range(w * h):
        if px[start] is None or seen[start]:
            continue
        stack, seen[start] = [start], 1
        x0 = x1 = start % w
        y0 = y1 = start // w
        while stack:
            p = stack.pop()
            x, y = p % w, p // w
            x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
            for q in (p - 1 if x else -1, p + 1 if x + 1 < w else -1, p - w, p + w):
                if 0 <= q < w * h and not seen[q] and px[q] is not None:
                    seen[q] = 1
                    stack.append(q)
        if x1 - x0 > 254 or y1 - y0 > 254:
            sys.exit(f"blob at {x0},{y0} too large for rects mode")
        found.append((x0, y0, x1 - x0 + 1, y1 - y0 + 1, px[start]))
    return found


def c_bytes(data: bytes) -> str:
    rows = [", ".join(f"0x{b:02X}" for b in data[i:i + 20]) for i in range(0, len(data), 20)]
    return "\n  " + ",\n  ".join(rows) + "\n"


def encode(name: str, frames: list, durations: list, tags: list, budget: int | None = None) -> tuple:
    """RLE-encode RGBA frames (trimmed to shared opaque bounds) into C++ source."""
    boxes = [f.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox() for f in frames]
    boxes = [b for b in boxes if b]
    if not boxes:
        sys.exit(f"{name}: no opaque pixels")
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    w, h = x1 - x0, y1 - y0
    parts, refs, total = [], [], 0
    for i, f in enumerate(frames):
        data = rle(to_pixels(f.crop((x0, y0, x1, y1))))
        total += len(data)
        parts.append(f"static const uint8_t {name}_f{i}[] = {{{c_bytes(data)}}};\n")
        refs.append(f"{{{name}_f{i}, {durations[i]}}}")
    if budget and total > budget:
        sys.exit(f"{name}: {total} bytes exceeds max_bytes {budget}")
    tag_rows = ", ".join(f'{{"{t}", {a}, {b}}}' for t, a, b in tags)
    tag_decl = f"static const AnimTag {name}_tags[] = {{{tag_rows}}};\n" if tags else ""
    tag_ref = f"{name}_tags" if tags else "nullptr"
    cpp = "".join(parts) + f"static const AnimFrame {name}_frames[] = {{{', '.join(refs)}}};\n" + tag_decl
    cpp += (f"const AnimAsset ASSET_{name} = {{{x0}, {y0}, {w}, {h}, {len(frames)}, {name}_frames, "
            f"{len(tags)}, {tag_ref}}};\n")
    return cpp, f"extern const AnimAsset ASSET_{name};  // {w}x{h}, {len(frames)} frames\n", total


def convert(entry: dict) -> tuple:
    name = entry["name"]
    frames, durations, tags = load(entry)
    if entry.get("mode") == "rects":
        found = rects(frames[0])
        body = ",\n  ".join(f"{{{x}, {y}, {w}, {h}, 0x{c:02X}}}" for x, y, w, h, c in found)
        cpp = (f"static const AnimRect {name}_rects[] = {{\n  {body}\n}};\n"
               f"const AnimRectSet RECTS_{name} = {{{len(found)}, {name}_rects}};\n")
        return cpp, f"extern const AnimRectSet RECTS_{name};  // {len(found)} rects\n", len(found) * 8
    return encode(name, frames, durations, tags, entry.get("max_bytes"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if generated files are stale")
    ap.add_argument("--profile", help="only compile the scenes this profile selects")
    a = ap.parse_args()
    manifest = json.loads((ASSETS / "manifest.json").read_text())
    cpp = ["// Generated by scripts/asset_convert.py from assets/manifest.json. Do not edit.\n",
           '#include "assets_gen.h"\n\n']
    hdr = ["// Generated by scripts/asset_convert.py. Do not edit.\n#pragma once\n", '#include "anim.h"\n\n']
    grand = 0
    for entry in manifest["assets"]:
        body, decl, size = convert(entry)
        cpp.append(body + "\n")
        hdr.append(decl)
        grand += size
        print(f"{entry['name']:<16} {size:>8} bytes")
    print(f"{'total':<16} {grand:>8} bytes")
    out = {FW / "assets_gen.cpp": "".join(cpp), FW / "assets_gen.h": "".join(hdr)}
    import scenes
    scpp, shdr, ssize = scenes.generate(a.profile)
    out[FW / "scenes_gen.cpp"], out[FW / "scenes_gen.h"] = scpp, shdr
    print(f"{'scenes':<16} {ssize:>8} bytes")
    if a.check:
        stale = [p.name for p, t in out.items() if not p.exists() or p.read_text() != t]
        sys.exit(("stale: " + ", ".join(stale)) if stale else 0)
    for p, t in out.items():
        p.write_text(t, newline="\n")


if __name__ == "__main__":
    main()
