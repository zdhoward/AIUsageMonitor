"""Audit which Studio settings each library entry shows versus what the engine uses.

Reads firmware/AIUsageMonitor/scene.cpp (fields each generator reads),
scripts/scenes.py's mapping of Studio fields to SceneGen fields, and every
assets/library/*/entry.json. Writes a JSON fact sheet per entry (and prints a
table) so reviewers - human or model - start from ground truth, not guesses.

Usage: python scripts/settings_audit.py [--json OUT.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE_CPP = ROOT / "firmware" / "AIUsageMonitor" / "scene.cpp"
LIBRARY = ROOT / "assets" / "library"

# Studio generator fields (studio/web/scene.js renderGen) -> SceneGen field (scenes.py gen_spec).
STUDIO_FIELDS = {
    "patterns": {"scale": "scale", "vx": "vx16", "vy": "vy16", "seconds": "seconds"},
    "plasma": {"scale": "scale"},
    "warp": {"speed": "vx16"},
    "matrix": {"scale": "scale", "speed": "vx16", "density": "vy16"},
    "fire": {"scale": "scale", "speed": "vx16", "density": "vy16"},
    "lava": {"scale": "scale", "speed": "vx16", "density": "vy16"},
    "aurora": {"scale": "scale", "speed": "vx16", "density": "vy16"},
    "life": {"scale": "scale", "speed": "vx16", "density": "vy16", "seconds": "seconds"},
    "ripple": {"scale": "scale", "density": "vy16"},
    "fireworks": {"speed": "vx16", "density": "vy16"},
    "videoeq": {"scale": "scale", "speed": "vx16", "mode": "vy16", "seconds": "seconds"},
    "spectre": {"scale": "scale", "speed": "vx16", "mode": "vy16", "seconds": "seconds"},
}
FUNCS = {"patterns": "drawPatterns", "plasma": "drawPlasma", "warp": "drawWarp", "matrix": "drawMatrix",
         "fire": "drawFire", "lava": "drawLava", "aurora": "drawAurora", "life": "drawLife", "ripple": "drawRipple",
         "fireworks": "drawFireworks", "videoeq": "drawVideoEq", "spectre": "drawSpectre"}


def function_bodies(src: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^static \w[\w\s\*&]*?\b(\w+)\(([^)]*)\)\s*\{", src, re.M):
        depth, i = 1, m.end()
        while depth and i < len(src):
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            i += 1
        out[m.group(1)] = src[m.end():i]
    return out


def fields_used(name: str, bodies: dict[str, str], seen: set | None = None) -> set[str]:
    """SceneGen fields a function reads, following calls into helpers that take the generator."""
    seen = seen or set()
    if name in seen or name not in bodies:
        return set()
    seen.add(name)
    body = bodies[name]
    used = {f for f in ("scale", "vx16", "vy16", "seconds", "tiles") if re.search(rf"\bg\.{f}\b", body)}
    if re.search(r"\bg\.colors?\b|\bg\.colorCount\b", body):
        used.add("colors")
    for callee in (set(re.findall(r"\b(\w+)\(", body)) & set(bodies)) - {"genKey"}:  # cache key: hashes every field
        if re.search(rf"\b{callee}\([^;]*\bg\b", body):
            used |= fields_used(callee, bodies, seen)
    return used


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write the fact sheets here")
    a = ap.parse_args()
    bodies = function_bodies(SCENE_CPP.read_text(encoding="utf-8"))
    sheets = []
    for f in sorted(LIBRARY.glob("*/entry.json")):
        e = json.loads(f.read_text(encoding="utf-8"))
        sc = e.get("scene") or {}
        g = sc.get("generator")
        sheet = {"id": f.parent.name, "name": e.get("name"), "kind": e.get("kind"), "notes": e.get("notes", ""),
                 "has_layers": bool(sc.get("layers")), "generator": g and g.get("type")}
        if e.get("kind") == "scene":
            dead, live = [], []
            # Sky gradient: drawn only when there is no generator (sceneDraw).
            (dead if g else live).append("sky top/bottom colours")
            if g:
                used = fields_used(FUNCS[g["type"]], bodies)
                for ui, field in STUDIO_FIELDS.get(g["type"], {}).items():
                    (live if field in used else dead).append(f"generator '{ui}' (-> {field})")
                (live if "colors" in used else dead).append(f"generator colours ({len(g.get('colors', []))} stops)")
            live.append("effects stars/rain/snow/lightning (drawn over any backdrop)")
            live.append("theme / theme shift (palette remap of the final frame)")
            sheet.update(current_settings={k: v for k, v in sc.items() if k not in ("layers",)},
                         layers=[{k: L.get(k) for k in ("src", "speed", "fit", "gap", "ms") if k in L}
                                 for L in sc.get("layers", [])],
                         controls_that_work=live, controls_that_do_nothing=dead)
        sheets.append(sheet)
        print(f"{sheet['id']:<16} {sheet['kind']:<6} gen={str(sheet['generator']):<10} "
              f"dead: {', '.join(sheet.get('controls_that_do_nothing', [])) or '-'}")
    if a.json:
        Path(a.json).write_text(json.dumps(sheets, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
