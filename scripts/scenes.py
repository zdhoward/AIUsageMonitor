"""Scene library -> firmware scene tables, theme palettes and Studio previews.

A scene is a library entry (assets/library/<id>/entry.json) with a "scene" object:

  background  {"top": "#hex", "bottom": "#hex"}       sky gradient
  theme       name from THEMES (palette remap applied on the device)
  variants    extra themes; each is its own playlist entry sharing the layer data
  cycle       {"themes": [...], "hold": s, "fade": s}: the scene itself cycles
              through these themes, cross-fading for `fade` seconds after holding
              each for `hold` seconds. Themes may be built in or palettes from
              assets/themes/*.json (e.g. imported from Lospec).
  layers[]    back to front:
    src       file or list of files (png/gif/aseprite) relative to the entry folder
    layer     optional Aseprite layer name
    speed     px/s scrolled leftwards (0 = static, centred); negative scrolls right
    y         top of the layer; default bottom-aligned on the 240 px scene
    scale     number (default 1), or "fit" to scale the source height to 240 px
    fit       for still pictures: original | pixel (largest whole-number zoom) |
              contain | cover (fill, cropping) | stretch; overrides scale and y
    gap       empty px between repeats (sprites that cross the screen)
    ms        frame time for multi-file layers
  effects[]   {"type": stars|rain|snow|lightning, "density": 1-3, "color": "#hex"}
  generator   optional procedural backdrop replacing the sky:
              {"type": "patterns", "tiles": [16x16 png...], "scale": 3, "vx": 12, "vy": 6,
               "seconds": 7, "colors": [bg, fg, bg, fg, ...]}
              {"type": "plasma", "scale": 2, "colors": [gradient stops]}
              {"type": "warp", "speed": 300, "colors": [space, ..., near star]}
              {"type": "matrix", "speed": 12, "density": 70, "scale": 1,
               "colors": [background, trail stops..., head]}

Semi-transparent pixels are blended over the sky gradient (a matte), so soft
glows such as a sun's halo survive the 1-bit transparency of the device format.
"""
from __future__ import annotations

import colorsys
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import asset_convert as ac  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "assets" / "library"
PROFILES = ROOT / "profiles"
SCENE_H = 240
FX = {"stars": 1, "rain": 2, "snow": 3, "lightning": 4}
FX_FRONT = {"rain", "snow"}
GEN = {"patterns": 1, "plasma": 2, "warp": 3, "matrix": 4}


def tile_bits(path: Path) -> bytes:
    """16x16 tile -> 32 bytes, 1 = light pixel, MSB on the left."""
    with Image.open(path) as im:
        im = im.convert("RGBA").resize((16, 16), Image.NEAREST)
    out = bytearray()
    for y in range(16):
        for half in range(2):
            v = 0
            for x in range(8):
                r, g, b, a = im.getpixel((half * 8 + x, y))
                v = (v << 1) | int(a >= 128 and (r + g + b) > 384)
            out.append(v)
    return bytes(out)


def gen_spec(entry_dir: Path, g: dict) -> dict:
    colors = [ac.rgb332(*hex_rgb(c)) for c in g.get("colors", ["#000000", "#ffffff"])]
    tiles = b"".join(tile_bits(entry_dir / t) for t in g.get("tiles", []))
    t = g["type"]
    speed = {"warp": g.get("speed", 300), "matrix": g.get("speed", 12)}.get(t, g.get("vx", 0))
    vy = g.get("density", 70) if t == "matrix" else g.get("vy", 0) * 16  # matrix: % of columns raining
    return {"type": GEN[t], "scale": int(g.get("scale", {"patterns": 3, "matrix": 1}.get(t, 2))),
            "vx16": int(speed * 16), "vy16": int(vy), "seconds": int(g.get("seconds", 7)),
            "tiles": tiles, "colors": colors}


# ------------------------------------------------------------------ themes
def _lum(r, g, b):
    return (0.3 * r + 0.59 * g + 0.11 * b) / 255


def _ramp(*stops):
    def f(r, g, b):
        t = _lum(r, g, b) * (len(stops) - 1)
        i = min(int(t), len(stops) - 2)
        u = t - i
        return tuple(int(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * u) for k in range(3))
    return f


def _hue(deg, sat=1.0, val=1.0):
    def f(r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        r2, g2, b2 = colorsys.hsv_to_rgb((h + deg / 360) % 1, min(1, s * sat), min(1, v * val))
        return int(r2 * 255), int(g2 * 255), int(b2 * 255)
    return f


THEMES = {
    "original": None,
    "vapor": _hue(55, 1.15),
    "toxic": _hue(120, 1.1),
    "dusk": _hue(-35, 1.1),
    "ice": _ramp((0, 0, 20), (20, 60, 140), (90, 190, 255), (230, 250, 255)),
    "matrix": _ramp((0, 0, 0), (0, 70, 20), (40, 200, 60), (190, 255, 190)),
    "amber": _ramp((0, 0, 0), (90, 30, 0), (255, 150, 20), (255, 230, 160)),
    "noir": _ramp((0, 0, 0), (60, 60, 70), (180, 180, 190), (255, 255, 255)),
    "night": lambda r, g, b: (int(r * .45), int(g * .5), int(min(255, b * .7 + 30))),
    "sunset": lambda r, g, b: (min(255, int(r * 1.1 + 40)), int(g * .8), int(b * .65)),
}


THEMES_DIR = ROOT / "assets" / "themes"


def palettes() -> dict:
    """Palette themes saved in assets/themes/<id>.json: {name, author, url, colors}."""
    out = {}
    for f in sorted(THEMES_DIR.glob("*.json")) if THEMES_DIR.is_dir() else []:
        out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return out


def theme_names() -> list[str]:
    return list(THEMES) + [p for p in palettes() if p not in THEMES]


def palette_lut(colors: list[str]) -> list[int]:
    """Gradient-map by brightness onto the palette, using only palette colours."""
    pal = sorted((hex_rgb(c if c.startswith("#") else "#" + c) for c in colors), key=lambda c: _lum(*c))
    n = len(pal)
    return [ac.rgb332(*pal[min(n - 1, int(_lum(*rgb_of(c)) * n))]) for c in range(256)]


def rgb_of(c: int) -> tuple:
    return ((c >> 5) & 7) * 255 // 7, ((c >> 2) & 7) * 255 // 7, (c & 3) * 85


def lut(theme: str) -> list | None:
    if theme not in THEMES:
        pal = palettes().get(theme)
        return palette_lut(pal["colors"]) if pal else None
    f = THEMES.get(theme)
    return None if f is None else [ac.rgb332(*f(*rgb_of(c))) for c in range(256)]


def theme_info() -> list[dict]:
    """For the Studio: every theme with a few swatch colours."""
    out = []
    for t in THEMES:
        table = lut(t) or list(range(256))
        sw = [table[ac.rgb332(*c)] for c in ((30, 10, 60), (220, 40, 160), (40, 200, 230), (255, 190, 80), (240, 240, 250))]
        out.append({"id": t, "name": t, "kind": "builtin", "colors": ["#%02x%02x%02x" % rgb_of(c) for c in sw]})
    for pid, p in palettes().items():
        out.append({"id": pid, "name": p.get("name", pid), "kind": "palette", "author": p.get("author", ""),
                    "url": p.get("url", ""), "colors": ["#" + c.lstrip("#") for c in p["colors"]]})
    return out


def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ layers
def load_frames(entry_dir: Path, layer: dict) -> tuple[list, list]:
    srcs = layer["src"] if isinstance(layer["src"], list) else [layer["src"]]
    frames, durations = [], []
    for src in srcs:
        path = entry_dir / src
        ext = path.suffix.lower()
        if ext == ".gif":
            f, d, _ = ac.load_gif(path)
        elif ext in (".aseprite", ".ase"):
            f, d, _ = ac.load_aseprite(path, layer.get("layer"))
        else:
            with Image.open(path) as im:
                f, d = [im.convert("RGBA")], [layer.get("ms", 100)]
        frames += f
        durations += d
    if len(srcs) > 1:
        durations = [layer.get("ms", 100)] * len(frames)
    return frames, durations


def sky_row(bg: dict, y: int) -> tuple:
    top, bot = hex_rgb(bg["top"]), hex_rgb(bg["bottom"])
    t = min(max(y, 0), SCENE_H - 1) / (SCENE_H - 1)
    return tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3))


def prepare_layer(entry_dir: Path, layer: dict, bg: dict) -> dict:
    frames, durations = load_frames(entry_dir, layer)
    w, h = frames[0].size
    scale = layer.get("scale", 1)
    k = SCENE_H / h if scale == "fit" else float(scale)
    if abs(k - 1) > 1e-3:
        size = (max(1, round(w * k)), max(1, round(h * k)))
        frames = [f.resize(size, Image.NEAREST) for f in frames]
    fit = layer.get("fit")
    if fit and fit != "original":
        fw, fh = frames[0].size
        k = {"pixel": max(1, int(min(320 / fw, SCENE_H / fh))), "contain": min(320 / fw, SCENE_H / fh),
             "cover": max(320 / fw, SCENE_H / fh)}.get(fit)
        size = (320, SCENE_H) if fit == "stretch" else (max(1, round(fw * k)), max(1, round(fh * k)))
        frames = [f.resize(size, Image.NEAREST) for f in frames]
        if fit == "cover":
            cx, cy = (size[0] - 320) // 2, (size[1] - SCENE_H) // 2
            frames = [f.crop((cx, cy, cx + 320, cy + SCENE_H)) for f in frames]
    w, h = frames[0].size
    y = (SCENE_H - h) // 2 if fit else layer.get("y", SCENE_H - h)
    out = []
    for f in frames:  # matte soft alpha against the sky behind it
        px = f.load()
        for yy in range(h):
            sr, sg, sb = sky_row(bg, y + yy)
            for xx in range(w):
                r, g, b, a = px[xx, yy]
                if 16 <= a < 250:
                    u = a / 255
                    px[xx, yy] = (int(r * u + sr * (1 - u)), int(g * u + sg * (1 - u)), int(b * u + sb * (1 - u)), 255)
                elif a < 16:
                    px[xx, yy] = (0, 0, 0, 0)
        out.append(f)
    return {"frames": out, "durations": durations, "y": y, "w": w, "h": h,
            "period": w + int(layer.get("gap", 0)), "speed": float(layer.get("speed", 0)),
            "frame_ms": int(layer.get("frame_ms", 0))}


def quantized(im: Image.Image) -> Image.Image:
    q = Image.new("RGBA", im.size)
    q.putdata([(*rgb_of(ac.rgb332(r, g, b)), 255) if a >= 128 else (0, 0, 0, 0) for r, g, b, a in im.getdata()])
    return q


def write_preview(entry_dir: Path, layers: list) -> None:
    """Quantized frame strips + metadata for the Studio's live preview."""
    out = entry_dir / ".build"
    out.mkdir(exist_ok=True)
    meta = []
    for i, L in enumerate(layers):
        strip = Image.new("RGBA", (L["w"] * len(L["frames"]), L["h"]))
        for j, f in enumerate(L["frames"]):
            strip.paste(quantized(f), (j * L["w"], 0))
        strip.save(out / f"layer{i}.png")
        meta.append({"w": L["w"], "h": L["h"], "y": L["y"], "frames": len(L["frames"]),
                     "durations": L["durations"], "url": f"layer{i}.png"})
    (out / "layers.json").write_text(json.dumps(meta), encoding="utf-8")


def write_gen_preview(entry_dir: Path, sc: dict) -> None:
    out = entry_dir / ".build"
    out.mkdir(exist_ok=True)
    g = sc.get("generator")
    data = None
    if g:
        spec = gen_spec(entry_dir, g)
        data = {**spec, "tiles": list(spec["tiles"])}
    (out / "gen.json").write_text(json.dumps(data), encoding="utf-8")


# ------------------------------------------------------------------ library
def library_scenes() -> list[tuple[str, Path, dict]]:
    found = []
    for f in sorted(LIBRARY.glob("*/entry.json")):
        e = json.loads(f.read_text(encoding="utf-8"))
        if e.get("kind") == "scene" and e.get("scene"):
            found.append((f.parent.name, f.parent, e))
    return found


def selected(profile: str | None) -> set | None:
    if not profile:
        return None
    f = PROFILES / f"{profile}.json"
    if not f.is_file():  # a profile being created: compile everything
        return None
    sel = json.loads(f.read_text(encoding="utf-8")).get("scenes", "all")
    return None if sel == "all" else set(sel)


def scene_themes(sc: dict) -> list[str]:
    return [sc.get("theme", "original")] + [t for t in sc.get("variants", []) if t != sc.get("theme")]


def scene_list(profile: str | None = None) -> list[dict]:
    """Compiled scenes in firmware order (SCENES[i]); variants follow their base."""
    want = selected(profile)
    out = []
    for sid, _, e in library_scenes():
        if want is not None and sid not in want:
            continue
        for k, theme in enumerate(scene_themes(e["scene"])):
            out.append({"id": sid if k == 0 else f"{sid}-{theme}", "entry": sid, "theme": theme,
                        "name": e.get("name", sid) + ("" if k == 0 else f" ({theme})")})
    return out


def prepare(entry_id: str) -> None:
    """Regenerate one scene's Studio preview (used after import or edits)."""
    d = LIBRARY / entry_id
    e = json.loads((d / "entry.json").read_text(encoding="utf-8"))
    sc = e["scene"]
    write_preview(d, [prepare_layer(d, L, sc["background"]) for L in sc["layers"]])


def c_name(s: str) -> str:
    return "sc_" + "".join(ch if ch.isalnum() else "_" for ch in s)


def generate(profile: str | None = None) -> tuple[str, str, int]:
    want = selected(profile)
    cpp = ["// Generated by scripts/asset_convert.py from assets/library. Do not edit.\n",
           '#include "scenes_gen.h"\n\n']
    defs, total = [], 0
    luts: dict[str, str] = {}
    for sid, d, e in library_scenes():
        if want is not None and sid not in want:
            continue
        sc, n = e["scene"], c_name(sid)
        layers = [prepare_layer(d, L, sc["background"]) for L in sc.get("layers", [])]
        write_preview(d, layers)
        write_gen_preview(d, sc)
        rows = []
        for i, L in enumerate(layers):
            body, _, size = ac.encode(f"{n}_l{i}", L["frames"], L["durations"], [])
            cpp.append(body.replace("const AnimAsset ASSET_", "static const AnimAsset ASSET_"))
            total += size
            rows.append(f"{{&ASSET_{n}_l{i}, {L['y']}, {int(round(L['speed'] * 16))}, {L['period']}, {L['frame_ms']}}}")
        if rows:
            cpp.append(f"static const SceneLayer {n}_layers[] = {{{', '.join(rows)}}};\n")
        gen = "nullptr"
        if sc.get("generator"):
            g = gen_spec(d, sc["generator"])
            if g["tiles"]:
                cpp.append(f"static const uint8_t {n}_tiles[] = {{{ac.c_bytes(g['tiles'])}}};\n")
            cpp.append(f"static const uint8_t {n}_gcol[] = {{{', '.join(f'0x{c:02X}' for c in g['colors'])}}};\n")
            cpp.append(f"static const SceneGen {n}_gen = {{{g['type']}, {g['scale']}, {g['vx16']}, {g['vy16']}, "
                       f"{g['seconds']}, {f'{n}_tiles' if g['tiles'] else 'nullptr'}, {len(g['tiles']) // 32}, "
                       f"{n}_gcol, {len(g['colors'])}}};\n")
            gen = f"&{n}_gen"
            total += len(g["tiles"]) + len(g["colors"])
        fx = [f"{{{FX[x['type']]}, {max(1, min(3, int(x.get('density', 2))))}, "
              f"0x{ac.rgb332(*hex_rgb(x.get('color', '#9fb4ff'))):02X}, {int(x['type'] in FX_FRONT)}}}"
              for x in sc.get("effects", []) if x.get("type") in FX]
        if fx:
            cpp.append(f"static const SceneEffect {n}_fx[] = {{{', '.join(fx)}}};\n")
        top, bot = hex_rgb(sc["background"]["top"]), hex_rgb(sc["background"]["bottom"])
        name = e.get("name", sid).replace('"', "'")

        def lut_ref(theme: str) -> str:
            table = lut(theme) or list(range(256))  # cycles need a real table for "original"
            key = theme if lut(theme) else "identity"
            if key not in luts:
                luts[key] = "lut_" + "".join(ch if ch.isalnum() else "_" for ch in key)
                cpp.append(f"static const uint8_t {luts[key]}[256] = {{{ac.c_bytes(bytes(table))}}};\n")
            return luts[key]

        cyc = sc.get("cycle") or {}
        cyc_themes = [t for t in cyc.get("themes", []) if t in theme_names()]
        cycle = "nullptr, 0, 0, 0"
        if len(cyc_themes) > 1:
            refs = [lut_ref(t) for t in cyc_themes]
            cpp.append(f"static const uint8_t* const {n}_cycle[] = {{{', '.join(refs)}}};\n")
            cycle = (f"{n}_cycle, {len(refs)}, {int(max(1, cyc.get('hold', 20)))}, "
                     f"{int(max(0, cyc.get('fade', 4)) * 10)}")
        themes = scene_themes(sc)
        for k, theme in enumerate(themes):
            ref = lut_ref(theme) if lut(theme) else "nullptr"
            vid = sid if k == 0 else f"{sid}-{theme}"
            vname = name if k == 0 else f"{name} ({theme})"
            defs.append(f'  {{"{vid}", "{vname}", {{{top[0]}, {top[1]}, {top[2]}}}, {{{bot[0]}, {bot[1]}, {bot[2]}}}, '
                        f"{f'{n}_layers' if rows else 'nullptr'}, {len(layers)}, {f'{n}_fx' if fx else 'nullptr'}, {len(fx)}, "
                        f"{ref}, {gen}, {cycle if k == 0 else 'nullptr, 0, 0, 0'}}}")
        cpp.append("\n")
    if defs:
        cpp.append("const SceneDef SCENES[] = {\n" + ",\n".join(defs) + "\n};\n")
    else:
        cpp.append("const SceneDef SCENES[1] = {};\n")
    cpp.append(f"const uint8_t SCENE_COUNT = {len(defs)};\n")
    hdr = ("// Generated by scripts/asset_convert.py. Do not edit.\n#pragma once\n#include \"scene.h\"\n\n"
           "extern const SceneDef SCENES[];\nextern const uint8_t SCENE_COUNT;\n")
    return "".join(cpp), hdr, total


if __name__ == "__main__":
    prepare(sys.argv[1])


# ------------------------------------------------------------------ studio helpers
def render_still(entry_dir: Path, sc: dict, layers: list) -> Image.Image:
    """First-frame composite at scroll offset 0, as a library thumbnail."""
    im = Image.new("RGBA", (320, SCENE_H))
    px = im.load()
    for y in range(SCENE_H):
        c = (*rgb_of(ac.rgb332(*sky_row(sc["background"], y))), 255)
        for x in range(320):
            px[x, y] = c
    for L in layers:
        f = quantized(L["frames"][0])
        if L["speed"] == 0:
            im.alpha_composite(f, ((320 - L["period"]) // 2, L["y"]) if L["period"] <= 320 else (0, L["y"]),
                               (0, 0) if L["period"] <= 320 else ((L["period"] - 320) // 2, 0))
        else:
            for x in range(0, 320, L["period"]):
                im.alpha_composite(f, (x, L["y"]))
    table = lut(sc.get("theme", "original"))
    if table:
        im.putdata([(*rgb_of(table[ac.rgb332(r, g, b)]), a) for r, g, b, a in im.getdata()])
    return im.convert("RGB")


def prepare_with_still(entry_id: str) -> None:
    d = LIBRARY / entry_id
    e = json.loads((d / "entry.json").read_text(encoding="utf-8"))
    sc = e["scene"]
    layers = [prepare_layer(d, L, sc["background"]) for L in sc.get("layers", [])]
    write_preview(d, layers)
    write_gen_preview(d, sc)
    if not sc.get("generator"):
        render_still(d, sc, layers).save(d / "preview.png")


def aseprite_layers(path: Path) -> list[str]:
    import subprocess
    out = subprocess.run([ac.aseprite_exe(), "-b", "--list-layers", str(path)], capture_output=True, text=True)
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def auto_scene(entry_dir: Path, files: list[str]) -> dict:
    """Build a starting scene from imported files: layers back to front with
    speeds that grow with depth, a sky sampled from the back layer."""
    layers = []
    for f in files:
        if Path(f).suffix.lower() in (".aseprite", ".ase"):
            names = aseprite_layers(entry_dir / f)
            layers += [{"src": f, "layer": n} for n in names] if len(names) > 1 else [{"src": f}]
        else:
            layers.append({"src": f})
    probe = [load_frames(entry_dir, L)[0][0] for L in layers]
    hmax = max(im.size[1] for im in probe)
    scale = "fit" if hmax > SCENE_H else 1
    k = SCENE_H / hmax if scale == "fit" else 1
    n = len(layers)
    for i, (L, im) in enumerate(zip(layers, probe)):
        L["scale"] = scale
        # A single picture stays still and centred; layered art scrolls faster toward the front.
        L["speed"] = 0 if n == 1 else round(4 * 15 ** (i / (n - 1)))  # 4 px/s at the back to 60 at the front
        if n == 1 and im.size[1] * k < SCENE_H:
            L["y"] = round((SCENE_H - im.size[1] * k) / 2)
    back = probe[0].convert("RGBA")
    def avg(row):
        px = [back.getpixel((x, row)) for x in range(back.size[0])]
        px = [p for p in px if p[3] > 128] or [(10, 10, 30, 255)]
        return "#%02x%02x%02x" % tuple(sum(p[i] for p in px) // len(px) for i in range(3))
    # Art shorter than the screen leaves sky above it: match its top edge so there is no band.
    short = back.size[1] * k < SCENE_H - 1
    return {"background": {"top": avg(0), "bottom": avg(0) if short else avg(back.size[1] - 1)}, "theme": "original",
            "variants": [], "layers": layers, "effects": []}
