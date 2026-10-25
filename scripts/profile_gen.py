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
PLAYLISTS_HEADER = ROOT / "firmware" / "AIUsageMonitor" / "playlists_gen.h"
PLAYLIST_BASE = 200  # UI_PLAYLIST_PAGE_BASE in config.h

PAGES = {  # profile name -> (page macro, enable macro or None when always present)
    "console": ("UI_PAGE_CONSOLE", None),
    "details": ("UI_PAGE_DETAILS", None),
    "companion": ("UI_PAGE_COMPANION", "UI_COMPANION_ENABLED"),
    "image": ("UI_PAGE_IMAGE", "UI_IMAGE_ENABLED"),
    "city": ("UI_PAGE_CITY", "UI_CITY_ENABLED"),
    "scenes": ("UI_PAGE_SCENES", "UI_SCENES_ENABLED"),
    "system": ("UI_PAGE_SYSTEM", None),
}
MAX_MS = 2147483647


SCENE_BASE = 100  # UI_SCENE_PAGE_BASE in config.h


def scene_index(profile: str | None) -> dict:
    import scenes
    return {s["id"]: i for i, s in enumerate(scenes.scene_list(profile))}


def page_macro(page: str, index: dict, playlists: list) -> str:
    """'console' etc. map to UI_PAGE_*; 'scene:<id>' maps to its single-scene page."""
    if page.startswith("scene:"):
        return str(SCENE_BASE + index[page[6:]])
    if page.startswith("playlist:"):
        return str(PLAYLIST_BASE + [pl["id"] for pl in playlists].index(page[9:]))
    return PAGES[page][0]


def load(name: str) -> dict:
    return json.loads((PROFILES / f"{name}.json").read_text(encoding="utf-8"))


def validate(p: dict) -> list[str]:
    errs = []
    pages = p.get("pages", [])
    index = scene_index(p.get("id"))
    for pg in pages:
        if pg.startswith("scene:"):
            if pg[6:] not in index:
                errs.append(f"scene '{pg[6:]}' is not in the library")
        elif pg not in PAGES and not pg.startswith("playlist:"):
            errs.append(f"unknown page '{pg}'")
    pl_ids = [pl.get("id") for pl in p.get("playlists", [])]
    if len(pl_ids) > 16:
        errs.append("at most 16 playlists")
    if len(set(pl_ids)) != len(pl_ids):
        errs.append("two playlists share an id")
    for pl in p.get("playlists", []):
        for sid in pl.get("scenes", []):
            if sid not in index:
                errs.append(f"playlist '{pl.get('name')}': scene '{sid}' is not in the library")
        if not 1 <= int(pl.get("seconds", 0)) <= 3600:
            errs.append(f"playlist '{pl.get('name')}': seconds must be 1-3600")
    for pg in pages + [s_page for s_page in [p.get("screensaver", {}).get("page", "")] if s_page]:
        if pg.startswith("playlist:") and pg[9:] not in pl_ids:
            errs.append(f"playlist '{pg[9:]}' does not exist")
    if len(set(pages)) != len(pages):
        errs.append("a page is listed twice")
    if "console" not in pages:  # home page for the long-press gesture
        errs.append("console page is required")
    if p.get("rotation") not in (0, 1, 2, 3):
        errs.append("rotation must be 0-3")
    s = p.get("screensaver", {})
    if s.get("enabled"):
        target = s.get("page", "")
        if target.startswith("scene:") and target[6:] not in index:
            errs.append(f"screensaver scene '{target[6:]}' is not in the library")
        elif not target.startswith(("scene:", "playlist:")) and (target not in PAGES or target in ("console", "details")):
            errs.append("screensaver must show Companion, Images, City, Scenes or a scene")
        for key in ("timeout_s",):
            if not 1 <= s.get(key, 0) * 1000 <= MAX_MS:
                errs.append("screensaver timeout out of range")
        for view in ("console", "details"):
            if not 1 <= s.get(view, {}).get("timeout_s", 0) * 1000 <= MAX_MS:
                errs.append(f"{view} timeout out of range")
    return errs


def rgb565(hexcolor: str) -> int:
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def header(p: dict) -> str:
    s = p.get("screensaver", {})
    on = bool(s.get("enabled"))
    lines = [f"// Generated from profiles/{p.get('id', 'profile')}.json by profile_gen.py. Do not edit.",
             "#pragma once",
             f"#define DISPLAY_ROTATION {p['rotation']}",
             f"#define SHOW_REMAINING {int(p.get('show_remaining', True))}"]
    index = scene_index(p.get("id"))
    for name, (_, enable) in PAGES.items():
        if enable:
            lines.append(f"#define {enable} {int(name in p['pages'])}")

    colors = p.get("colors", {})
    for key, macro in (("healthy", "UI_COLOR_HEALTHY"), ("warning", "UI_COLOR_WARNING"), ("critical", "UI_COLOR_CRITICAL")):
        if colors.get(key):
            lines.append(f"#define {macro} 0x{rgb565(colors[key]):04X}")
    if colors.get("weekly"):  # "levels" = same threshold colours as the session ring
        lines.append(f"#define UI_WEEKLY_COLOR {0 if colors['weekly'] == 'levels' else hex(rgb565(colors['weekly']))}")
    lines.append(f"#define UI_SCENE_SECONDS {int(p.get('scene_seconds', 90))}")
    lines.append("#define UI_VIEW_ORDER " + ", ".join(page_macro(pg, index, p.get("playlists", [])) for pg in p["pages"]))
    lines += [f"#define UI_SCREENSAVER_ENABLED {int(on)}",
              f"#define UI_SCREENSAVER_AUTO_ENABLED {int(on)}"]
    if on:
        lines += [f"#define UI_SCREENSAVER_PAGE {page_macro(s['page'], index, p.get('playlists', []))}",
                  f"#define UI_SCREENSAVER_TIMEOUT_MS {int(s['timeout_s'] * 1000)}UL"]
        for view in ("console", "details"):
            v = s[view]
            up = view.upper()
            lines += [f"#define UI_{up}_SAVER_ENABLED {int(v.get('enabled', True))}",
                      f"#define UI_{up}_SAVER_TIMEOUT_MS {int(v['timeout_s'] * 1000)}UL",
                      f"#define UI_{up}_WAKE_ON_USAGE {int(v.get('wake_on_usage', True))}"]
    return "\n".join(lines) + "\n"


def playlists_header(p: dict, index: dict) -> str:
    out = [f"// Generated from profiles/{p.get('id', 'profile')}.json by profile_gen.py. Do not edit.",
           "#pragma once"]
    rows = []
    for k, pl in enumerate(p.get("playlists", [])):
        ids = [str(index[s]) for s in pl.get("scenes", [])] or ["0"]
        out.append(f"static const uint8_t kPl{k}[] = {{{', '.join(ids)}}};  // {pl.get('name', '')}")
        weather = int(pl.get("weather") == "random")  # "random": clear/rain/snow/storm per scene turn
        rows.append(f"  {{kPl{k}, {len(pl.get('scenes', []))}, {int(pl.get('seconds', 60))}, {weather}}}")
    out.append("static const Playlist kPlaylists[] = {\n" + (",\n".join(rows) or "  {nullptr, 0, 0, 0}") + "\n};")
    out.append(f"static const uint8_t kPlaylistCount = {len(rows)};")
    return "\n".join(out) + "\n"


def write(name: str) -> Path:
    p = load(name)
    p["id"] = name
    errs = validate(p)
    if errs:
        raise ValueError("; ".join(errs))
    HEADER.write_text(header(p), encoding="utf-8", newline="\n")
    PLAYLISTS_HEADER.write_text(playlists_header(p, scene_index(name)), encoding="utf-8", newline="\n")
    return HEADER


if __name__ == "__main__":
    try:
        print(f"wrote {write(sys.argv[1])}")
    except (ValueError, IndexError, FileNotFoundError) as e:
        sys.exit(f"profile error: {e}")
