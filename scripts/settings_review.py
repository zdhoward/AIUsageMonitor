"""Ask a local Ollama model for settings recommendations, one library entry at a time.

Input is the fact sheet from settings_audit.py (ground truth about which controls
work), so the model judges usefulness and clutter rather than guessing behaviour.
Writes one JSON recommendation per entry plus a combined Markdown report.

Usage: python scripts/settings_review.py FACTS.json OUT_DIR [--model gemma4:e4b] [--only id,id]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

CONTEXT = """You review settings for one item in "Scene Studio", a desktop app for a small 320x240 USB display (RGB332, 8-bit colour).
Users are hobbyists who want to be creative without being overwhelmed.
Every scene's settings panel currently shows, in this order:
- Theme picker + "theme shift" (smooth cross-fade through ticked palettes; hold/fade seconds)
- Layers (only scenes built from image layers): speed px/s, frame ms, fit or gap
- Generator section (only procedural scenes): numeric fields listed below + a colour-stop list (add/remove)
- Effects: stars / rain / snow / lightning, each Off/Light/Medium/Heavy, plus a colour (not lightning)
- Sky gradient: top and bottom colour pickers
The FACTS block is ground truth from the engine source: trust it over your assumptions.
Answer ONLY with JSON of this shape:
{"hide": [{"control": str, "why": str}],
 "keep_prominent": [str],
 "move_to_advanced": [{"control": str, "why": str}],
 "add": [{"control": str, "why": str, "effort": "small|medium|large"}],
 "label_or_hint_changes": [{"control": str, "new_label": str}],
 "default_changes": [{"setting": str, "value": str, "why": str}],
 "summary": str}
Rules: hide every control in controls_that_do_nothing. Suggest at most 3 additions and only ones the engine could plausibly support.
Keep it short and concrete."""


def ask(model: str, sheet: dict, timeout: int = 300) -> dict:
    body = {"model": model, "prompt": f"{CONTEXT}\n\nFACTS:\n{json.dumps(sheet, indent=1)}", "format": "json",
            "stream": False, "options": {"temperature": 0.2, "num_ctx": 8192}}
    req = urllib.request.Request("http://localhost:11434/api/generate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(json.loads(r.read())["response"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("facts")
    ap.add_argument("out")
    ap.add_argument("--model", default="gemma4:e4b")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    only = set(filter(None, a.only.split(",")))
    for sheet in json.loads(Path(a.facts).read_text(encoding="utf-8")):
        if sheet["kind"] != "scene" or (only and sheet["id"] not in only):
            continue
        t = time.time()
        try:
            rec = ask(a.model, sheet)
        except Exception as e:  # keep going; a failed entry is reported, not fatal
            rec = {"error": f"{type(e).__name__}: {e}"}
        rec["_model"], rec["_seconds"] = a.model, round(time.time() - t, 1)
        (out / f"{sheet['id']}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
        print(f"{sheet['id']:<16} {rec['_seconds']:>6}s {'ERROR ' + rec['error'] if 'error' in rec else rec.get('summary', '')[:90]}",
              flush=True)


if __name__ == "__main__":
    main()
