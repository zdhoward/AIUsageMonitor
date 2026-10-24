"""Bootstrap the city scene's pixel art as editable Aseprite files.

One-off generator: after it runs, the .aseprite files in assets/scenes/city/
are the source of truth. Edit them in Aseprite, then run asset_convert.py.
Re-running this script overwrites your edits (it refuses unless --force).

Colours are snapped to RGB332 levels so what you draw is what the panel shows.
Usage: python scripts/gen_city_art.py [--force] [--seed N]
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "scenes" / "city"
W, H, HORIZON = 320, 240, 168
sys.path.insert(0, str(Path(__file__).parent))
from asset_convert import aseprite_exe  # noqa: E402

# RGB332-exact palette (R,G in 8 levels; B in 4).
FAR = (73, 0, 85)
FAR_LIT = (146, 36, 170)
NEAR = (36, 0, 85)
NEAR_EDGE = (73, 36, 170)
CYAN = (0, 219, 255)
MAGENTA = (255, 0, 170)
RED = (255, 36, 0)
WINDOWS = [(255, 182, 85), (255, 219, 85), (0, 219, 255), (255, 109, 170)]


def far_layer(rng: random.Random) -> Image.Image:
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    x = -4
    while x < W:
        w = rng.randint(10, 26)
        centre = abs((x + w / 2) - W / 2) < 50
        h = rng.randint(14, 34) if centre else rng.randint(30, 82)
        top = HORIZON - h
        d.rectangle([x, top, x + w - 1, HORIZON - 1], fill=FAR)
        if rng.random() < 0.3:  # stepped roof
            d.rectangle([x + 3, top - 5, x + w - 4, top], fill=FAR)
        for _ in range(w * h // 60):  # dim static windows
            d.point((rng.randrange(x + 1, x + w - 1), rng.randrange(top + 3, HORIZON - 2)), fill=FAR_LIT)
        x += w + rng.choice([0, 0, 1, 2])
    return im


def near_layers(rng: random.Random) -> tuple[Image.Image, Image.Image, list]:
    im = Image.new("RGBA", (W, H))
    win = Image.new("RGBA", (W, H))
    d, dw = ImageDraw.Draw(im), ImageDraw.Draw(win)
    blocks = []
    for side in (range(-6, 118), range(206, W + 6)):  # keep the sun's gap clear
        x = side.start
        while x < side.stop:
            w = min(rng.randint(20, 40), side.stop - x)
            if w < 12:
                break
            h = rng.randint(60, 140)
            top = HORIZON - h
            d.rectangle([x, top, x + w - 1, HORIZON - 1], fill=NEAR)
            d.line([x, top, x, HORIZON - 1], fill=NEAR_EDGE)  # lit edge
            trim = rng.choice([CYAN, MAGENTA, None])
            if trim:
                d.line([x, top, x + w - 1, top], fill=trim)
            if rng.random() < 0.5:  # antenna with warning light
                ax = x + rng.randint(3, w - 4)
                d.line([ax, top - 12, ax, top - 1], fill=NEAR)
                d.point((ax, top - 13), fill=RED)
            colour = rng.choice(WINDOWS)
            for wy in range(top + 5, HORIZON - 4, 6):
                for wx in range(x + 3, x + w - 4, 5):
                    if rng.random() < 0.45:
                        c = colour if rng.random() < 0.8 else rng.choice(WINDOWS)
                        dw.rectangle([wx, wy, wx + 1, wy + 2], fill=c)
            blocks.append((x, top, w, h))
            x += w + rng.choice([1, 2, 4])
    return im, win, blocks


GLYPHS = {  # 5x5
    "A": ["01110", "10001", "11111", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "11111"],
}


def sign_frames() -> list[Image.Image]:
    def draw(lit: bool) -> Image.Image:
        im = Image.new("RGBA", (13, 22))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 12, 21], fill=(0, 0, 0), outline=CYAN if lit else (0, 73, 85))
        fg = MAGENTA if lit else (73, 0, 85)
        for gi, ch in enumerate("AI"):
            for r, row in enumerate(GLYPHS[ch]):
                for c, bit in enumerate(row):
                    if bit == "1":
                        d.point((4 + c, 4 + gi * 8 + r), fill=fg)
        return im
    return [draw(True), draw(False), draw(True), draw(False)]


def car_frames() -> list[Image.Image]:
    frames = []
    for tail in (RED, (109, 0, 0)):
        im = Image.new("RGBA", (18, 7))
        d = ImageDraw.Draw(im)
        d.rectangle([2, 3, 15, 5], fill=(73, 36, 170))      # hull
        d.rectangle([5, 1, 11, 2], fill=(0, 146, 170))      # canopy
        d.point((6, 1), fill=CYAN)
        d.line([2, 6, 15, 6], fill=MAGENTA)                 # underglow
        d.point((16, 4), fill=(255, 255, 170))              # headlight (faces right)
        d.point((1, 4), fill=tail)
        frames.append(im)
    return frames


def build(spec: dict, tmp: Path) -> None:
    path = tmp / (Path(spec["out"]).stem + ".json")
    path.write_text(json.dumps(spec))
    subprocess.run([aseprite_exe(), "-b", "--script-param", f"spec={path}",
                    "--script", str(Path(__file__).with_name("aseprite_build.lua"))], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--seed", type=int, default=2077)
    a = ap.parse_args()
    if (OUT / "city.aseprite").exists() and not a.force:
        sys.exit("city art exists; pass --force to overwrite your edits")
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    far = far_layer(rng)
    near, win, _ = near_layers(rng)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)

        def save(im: Image.Image, name: str) -> str:
            p = tmp / f"{name}.png"
            im.save(p)
            return p.as_posix()

        build({"w": W, "h": H, "out": (OUT / "city.aseprite").as_posix(), "durations": [100],
               "layers": [{"name": "far", "frames": [save(far, "far")]},
                          {"name": "near", "frames": [save(near, "near")]},
                          {"name": "windows", "frames": [save(win, "windows")]}]}, tmp)
        sf = sign_frames()
        build({"w": 13, "h": 22, "out": (OUT / "sign.aseprite").as_posix(), "durations": [1400, 70, 110, 60],
               "layers": [{"name": "sign", "frames": [save(f, f"sign{i}") for i, f in enumerate(sf)]}],
               "tags": [{"name": "flicker", "from": 1, "to": 4}]}, tmp)
        cf = car_frames()
        build({"w": 18, "h": 7, "out": (OUT / "car.aseprite").as_posix(), "durations": [300, 300],
               "layers": [{"name": "car", "frames": [save(f, f"car{i}") for i, f in enumerate(cf)]}],
               "tags": [{"name": "fly", "from": 1, "to": 2}]}, tmp)
    print(f"wrote city.aseprite, sign.aseprite, car.aseprite to {OUT}")


if __name__ == "__main__":
    main()
