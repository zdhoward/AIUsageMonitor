"""Turn a device profile (profiles/<name>.json) into firmware/AIUsageMonitor/profile_gen.h.

config.h includes profile_gen.h first, so these defines override its defaults.
Usage: python scripts/profile_gen.py <name>    (validates, then writes the header)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "profiles"
HEADER = ROOT / "firmware" / "AIUsageMonitor" / "profile_gen.h"

PAGES = {  # profile name -> (page macro, enable macro or None when always present)
    "console": ("UI_PAGE_CONSOLE", None),
    "details": ("UI_PAGE_DETAILS", None),
    "companion": ("UI_PAGE_COMPANION", "UI_COMPANION_ENABLED"),
    "image": ("UI_PAGE_IMAGE", "UI_IMAGE_ENABLED"),
    "city": ("UI_PAGE_CITY", "UI_CITY_ENABLED"),
}
MAX_MS = 2147483647


def load(name: str) -> dict:
    return json.loads((PROFILES / f"{name}.json").read_text(encoding="utf-8"))


def validate(p: dict) -> list[str]:
    errs = []
    pages = p.get("pages", [])
    for pg in pages:
        if pg not in PAGES:
            errs.append(f"unknown page '{pg}'")
    if len(set(pages)) != len(pages):
        errs.append("a page is listed twice")
    for required in ("console", "details"):
        if required not in pages:
            errs.append(f"{required} page is required")
    if p.get("rotation") not in (0, 1, 2, 3):
        errs.append("rotation must be 0-3")
    s = p.get("screensaver", {})
    if s.get("enabled"):
        if s.get("page") not in pages or s.get("page") in ("console", "details"):
            errs.append("screensaver must show an enabled Companion, Images or City page")
        for key in ("timeout_s",):
            if not 1 <= s.get(key, 0) * 1000 <= MAX_MS:
                errs.append("screensaver timeout out of range")
        for view in ("console", "details"):
            if not 1 <= s.get(view, {}).get("timeout_s", 0) * 1000 <= MAX_MS:
                errs.append(f"{view} timeout out of range")
    return errs


def header(p: dict) -> str:
    s = p.get("screensaver", {})
    on = bool(s.get("enabled"))
    lines = [f"// Generated from profiles/{p.get('id', 'profile')}.json by profile_gen.py. Do not edit.",
             "#pragma once",
             f"#define DISPLAY_ROTATION {p['rotation']}",
             f"#define SHOW_REMAINING {int(p.get('show_remaining', True))}"]
    for name, (_, enable) in PAGES.items():
        if enable:
            lines.append(f"#define {enable} {int(name in p['pages'])}")
    lines.append("#define UI_VIEW_ORDER " + ", ".join(PAGES[pg][0] for pg in p["pages"]))
    lines += [f"#define UI_SCREENSAVER_ENABLED {int(on)}",
              f"#define UI_SCREENSAVER_AUTO_ENABLED {int(on)}"]
    if on:
        lines += [f"#define UI_SCREENSAVER_PAGE {PAGES[s['page']][0]}",
                  f"#define UI_SCREENSAVER_TIMEOUT_MS {int(s['timeout_s'] * 1000)}UL"]
        for view in ("console", "details"):
            v = s[view]
            up = view.upper()
            lines += [f"#define UI_{up}_SAVER_ENABLED {int(v.get('enabled', True))}",
                      f"#define UI_{up}_SAVER_TIMEOUT_MS {int(v['timeout_s'] * 1000)}UL",
                      f"#define UI_{up}_WAKE_ON_USAGE {int(v.get('wake_on_usage', True))}"]
    return "\n".join(lines) + "\n"


def write(name: str) -> Path:
    p = load(name)
    p["id"] = name
    errs = validate(p)
    if errs:
        raise ValueError("; ".join(errs))
    HEADER.write_text(header(p), encoding="utf-8", newline="\n")
    return HEADER


if __name__ == "__main__":
    try:
        print(f"wrote {write(sys.argv[1])}")
    except (ValueError, IndexError, FileNotFoundError) as e:
        sys.exit(f"profile error: {e}")
