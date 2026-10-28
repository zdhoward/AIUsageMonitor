#!/usr/bin/env python3
"""Third-party component inventory, license auditing, and optional-content acquisition.

Usage:
    python scripts/third_party.py --help
    python scripts/third_party.py list [--format {text,json,markdown}] [--unverified-only]
    python scripts/third_party.py check [--strict]
    python scripts/third_party.py fetch --palette <slug|url> [--replace] --ack-source-terms
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "third_party" / "manifest.json"
THEMES_DIR = ROOT / "assets" / "themes"
LOGS_DIR = ROOT / "logs"

# Security constraints for optional fetching
ALLOWLISTED_HOSTS = {"lospec.com"}
ALLOWLISTED_PALETTES = {"neon-pulse-8"}
ALLOWLISTED_PATH_RE = re.compile(r"^/palette-list/([a-z0-9-]+)(?:\.json)?$")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")
HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")
MAX_FETCH_BYTES = 32 * 1024  # 32 KB ceiling
REQUEST_TIMEOUT = 15  # seconds


class RestrictRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Disallow host- or scheme-changing redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https":
            raise urllib.error.HTTPError(
                req.full_url,
                code,
                f"Disallowed redirect to non-HTTPS scheme: {newurl}",
                headers,
                fp,
            )
        if parsed.netloc.lower() not in ALLOWLISTED_HOSTS:
            raise urllib.error.HTTPError(
                req.full_url,
                code,
                f"Disallowed redirect to non-allowlisted host: {newurl}",
                headers,
                fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_list(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    components = manifest.get("components", [])

    if args.unverified_only:
        components = [c for c in components if not c.get("redistribution_verified", False)]

    if args.format == "json":
        print(json.dumps(components, indent=2))
        return 0

    if args.format == "markdown":
        print("| Component ID | Name | License | Status | Tracked Paths | Redistribution Verified |")
        print("|---|---|---|---|---|---|")
        for c in components:
            tracked = ", ".join(c.get("tracked_paths", [])) or "*(none / external)*"
            verified = "Yes" if c.get("redistribution_verified") else "**No (Unverified)**"
            print(f"| `{c['id']}` | {c['name']} | {c['license_spdx']} | {c['distribution_status']} | {tracked} | {verified} |")
        return 0

    # Default text format
    print(f"=== Third-Party Component Inventory ({len(components)} items) ===")
    print()
    for c in components:
        ver_str = "VERIFIED" if c.get("redistribution_verified") else "UNVERIFIED"
        print(f"[{ver_str}] {c['name']} ({c['id']})")
        print(f"  Category:       {c.get('category')}")
        print(f"  License:        {c.get('license_spdx')} (Evidence: {c.get('license_evidence_url')})")
        print(f"  Upstream:       {c.get('upstream_url')}")
        print(f"  Revision/Ver:   {c.get('revision_or_version')}")
        print(f"  Status:         {c.get('distribution_status')}")
        tracked = c.get("tracked_paths", [])
        if tracked:
            print(f"  Tracked files:  {', '.join(tracked)}")
        if not c.get("redistribution_verified"):
            print(f"  Gaps / Notes:   {c.get('uncertainty_and_gaps')}")
            if c.get("coordinator_action"):
                print(f"  Action:         {c.get('coordinator_action')}")
        print()
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    components = manifest.get("components", [])
    tracked = set(subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0"))

    print("Notice: This check reports limited inventory coverage for declared manifest components only.")
    print("It does not certify legality or provide legal assurances.")
    print()
    print("Auditing declared manifest components and tracked notices...")
    print()

    unverified_tracked = []
    unshipped_gaps = []
    missing_files = []
    verified_count = 0

    # 1. Verify known manifest notices
    # Grobot license notice
    grobot_license = ROOT / "firmware" / "AIUsageMonitor" / "grobot" / "LICENSE.txt"
    if not grobot_license.is_file():
        missing_files.append(("grobot", "firmware/AIUsageMonitor/grobot/LICENSE.txt (Grobot MIT notice)"))

    # SunriseSunset.io attribution notice
    brightness_py = ROOT / "service" / "aimon" / "brightness.py"
    if not brightness_py.is_file():
        missing_files.append(("sunrisesunset-api", "service/aimon/brightness.py"))
    else:
        b_text = brightness_py.read_text(encoding="utf-8")
        if "SunriseSunset.io" not in b_text or "https://sunrisesunset.io" not in b_text:
            missing_files.append(("sunrisesunset-api", "service/aimon/brightness.py (missing required SunriseSunset.io attribution notice/link)"))

    # 2. Check components
    for c in components:
        tracked_paths = c.get("tracked_paths", [])
        verified = c.get("redistribution_verified", False)
        category = c.get("category", "")

        # Check declared tracked files exist on disk
        for p in tracked_paths:
            full_path = ROOT / p
            if p in tracked and not full_path.exists():
                missing_files.append((c["id"], p))

        # Check redistribution verification status
        if verified:
            verified_count += 1
        else:
            if category in ("procedural_inspiration", "untracked_asset_pack"):
                unshipped_gaps.append(c)
            else:
                for p in tracked_paths:
                    if p in tracked:
                        unverified_tracked.append((c, p))

    # Summary
    print(f"Components in inventory:               {len(components)}")
    print(f"Verified components:                   {verified_count}")
    print(f"Missing declared files / notices:      {len(missing_files)}")
    print(f"Unverified tracked components:         {len(unverified_tracked)}")
    print(f"Unshipped asset & inspiration gaps:    {len(unshipped_gaps)}")
    print()

    if unshipped_gaps:
        print("[INFO] Unshipped assets and procedural inspirations with unverified upstream source / license gaps (no distribution failure):")
        for comp in unshipped_gaps:
            print(f"  - [{comp['id']}] {comp['name']}")
            print(f"    License:      {comp.get('license_spdx')}")
            print(f"    Gaps / Notes: {comp.get('uncertainty_and_gaps')}")
        print()

    if missing_files:
        print("[FAIL] Missing declared tracked files or required notices:")
        for comp_id, p in missing_files:
            print(f"  - [{comp_id}] {p}")
        print()

    if unverified_tracked:
        print("[FAIL] Unverified TRACKED content found in repository:")
        for comp, p in unverified_tracked:
            print(f"  - Tracked file: {p}")
            print(f"    Component:    {comp['name']} ({comp['id']})")
            print(f"    License:      {comp['license_spdx']}")
            print(f"    Evidence URL: {comp.get('license_evidence_url')}")
            print(f"    Gaps:         {comp.get('uncertainty_and_gaps')}")
            if comp.get("coordinator_action"):
                print(f"    Action:       {comp.get('coordinator_action')}")
        print()
        print("DEFAULT AUDIT FAILURE: Tracked files with unverified redistribution permission exist.")
        print("Recommended remediation: Untrack unverified files from git and acquire via local optional workflow.")
        return 1

    if missing_files:
        return 1

    print("[PASS] Declared manifest notices verified; no unverified tracked content found in inventory.")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    raw_target = args.palette or args.url
    if not raw_target:
        print("Error: Specify a palette slug or URL to fetch (e.g. --palette neon-pulse-8)", file=sys.stderr)
        return 2

    # Normalise slug or URL
    if raw_target.startswith("http://") or raw_target.startswith("https://"):
        parsed = urllib.parse.urlparse(raw_target)
        if parsed.scheme != "https":
            print(f"Error: Insecure scheme '{parsed.scheme}'. Only HTTPS is permitted.", file=sys.stderr)
            return 2
        if parsed.netloc.lower() not in ALLOWLISTED_HOSTS:
            print(f"Error: Host '{parsed.netloc}' is not in allowlisted upstream hosts ({sorted(ALLOWLISTED_HOSTS)}).", file=sys.stderr)
            return 2
        match = ALLOWLISTED_PATH_RE.match(parsed.path)
        if not match:
            print(f"Error: Path '{parsed.path}' does not match allowlisted Lospec palette format.", file=sys.stderr)
            return 2
        slug = match.group(1).lower()
    else:
        slug = raw_target.strip().rstrip("/").split("/")[-1].removesuffix(".json").lower()
        if not SLUG_RE.match(slug):
            print(f"Error: Invalid palette slug '{slug}'. Must be alphanumeric with hyphens.", file=sys.stderr)
            return 2

    if slug not in ALLOWLISTED_PALETTES:
        print(f"Error: Palette '{slug}' is not in allowlisted known palette requests ({sorted(ALLOWLISTED_PALETTES)}).", file=sys.stderr)
        return 2

    upstream_url = f"https://lospec.com/palette-list/{slug}.json"
    terms_url = "https://lospec.com/terms-and-conditions"

    print(f"Target upstream: {upstream_url}")
    print(f"Source terms:    {terms_url}")

    if not args.ack_source_terms:
        print()
        print("[ACKNOWLEDGEMENT REQUIRED]", file=sys.stderr)
        print("Lospec website terms (https://lospec.com/terms-and-conditions) govern access to palette data.", file=sys.stderr)
        print("Redistribution permission for this palette is unverified. To acquire this content locally,", file=sys.stderr)
        print("you must re-run with --ack-source-terms.", file=sys.stderr)
        print()
        print("NOTE: User acknowledgement records local compliance with upstream site terms;", file=sys.stderr)
        print("it DOES NOT create rights, grant personal-use permissions, or grant redistribution rights.", file=sys.stderr)
        return 2

    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = (THEMES_DIR / f"{slug}.json").resolve()
    if out_path.parent != THEMES_DIR.resolve() or not out_path.is_relative_to(ROOT.resolve()):
        print("Error: Palette destination must stay inside the repository themes directory.", file=sys.stderr)
        return 2

    if out_path.exists() and not args.replace:
        print(f"Error: Target file '{out_path}' already exists. Use --replace to overwrite.", file=sys.stderr)
        return 1

    # Bounded fetch with restricted redirect handling
    print("Requesting palette data (bounded to 32 KB, timeout 15s)...")
    opener = urllib.request.build_opener(RestrictRedirectHandler())
    req = urllib.request.Request(
        upstream_url,
        headers={"User-Agent": "AIUsageMonitor-ThirdParty/1.0 (stdlib; local acquisition)"},
    )

    try:
        with opener.open(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read(MAX_FETCH_BYTES + 1)
            if len(data) > MAX_FETCH_BYTES:
                print(f"Error: Response exceeded maximum allowed size ({MAX_FETCH_BYTES} bytes). Aborting.", file=sys.stderr)
                return 1
    except Exception as e:
        print(f"Error: Failed to fetch upstream palette: {e}", file=sys.stderr)
        return 1

    sha256_hash = hashlib.sha256(data).hexdigest()

    # Parse and validate JSON structure strictly
    try:
        raw_json = json.loads(data.decode("utf-8"))
    except Exception as e:
        print(f"Error: Response is not valid JSON: {e}", file=sys.stderr)
        return 1

    if not isinstance(raw_json, dict):
        print("Error: Response root must be a JSON dictionary.", file=sys.stderr)
        return 1

    palette_name = str(raw_json.get("name", slug)).strip()
    author = str(raw_json.get("author", "")).strip()
    raw_colors = raw_json.get("colors", [])

    if len(palette_name) > 64:
        print("Error: Palette name exceeds maximum length of 64 characters.", file=sys.stderr)
        return 1
    if len(author) > 64:
        print("Error: Author string exceeds maximum length of 64 characters.", file=sys.stderr)
        return 1

    if not isinstance(raw_colors, list) or len(raw_colors) < 2 or len(raw_colors) > 256:
        print("Error: Palette colors must be a list containing between 2 and 256 colors.", file=sys.stderr)
        return 1

    clean_colors = []
    for c in raw_colors:
        c_str = str(c).strip().lstrip("#").lower()
        if not HEX_RE.match(c_str):
            print(f"Error: Invalid hex color '{c}'. Only 6-digit hex values are allowed.", file=sys.stderr)
            return 1
        clean_colors.append(c_str)

    palette_entry = {
        "name": palette_name,
        "author": author,
        "url": f"https://lospec.com/palette-list/{slug}",
        "source": "lospec",
        "license_status": "unverified_source_terms_acknowledged",
        "acquired_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "colors": clean_colors,
    }

    # Atomic write
    tmp_path = out_path.with_suffix(f".tmp.{os.getpid()}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(palette_entry, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, out_path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        print(f"Error: Failed to save palette atomically: {e}", file=sys.stderr)
        return 1

    # Write acquisition receipt in ignored logs
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    receipt_file = LOGS_DIR / "third_party_receipts.jsonl"
    receipt = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "slug": slug,
        "upstream_url": upstream_url,
        "terms_url": terms_url,
        "terms_acknowledged": True,
        "destination": str(out_path),
        "sha256": sha256_hash,
        "author": author,
        "color_count": len(clean_colors),
        "notice": "User acknowledged source terms. Local acquisition only; does not create rights, grant personal-use permissions, or grant redistribution rights.",
    }

    with open(receipt_file, "a", encoding="utf-8") as rf:
        rf.write(json.dumps(receipt) + "\n")

    print()
    print(f"[SUCCESS] Saved palette to git-ignored location: {out_path}")
    print(f"Acquisition receipt written to: {receipt_file}")
    print("Important: This local file is git-ignored. Acquisition does not establish use or redistribution rights.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit third-party dependencies, licenses, and acquire optional content safely."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List third-party components from manifest")
    p_list.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output format")
    p_list.add_argument("--unverified-only", action="store_true", help="Filter for unverified components")
    p_list.set_defaults(func=cmd_list)

    # check
    p_check = subparsers.add_parser("check", help="Audit tracked files and license verification")
    p_check.add_argument("--strict", action="store_true", help="Exit with non-zero code if unverified tracked files exist")
    p_check.set_defaults(func=cmd_check)

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="Safely acquire optional upstream palette data")
    p_fetch.add_argument("--palette", help="Palette slug or URL (e.g. neon-pulse-8)")
    p_fetch.add_argument("--url", help="Full upstream URL")
    p_fetch.add_argument("--replace", action="store_true", help="Overwrite existing local palette file")
    p_fetch.add_argument("--ack-source-terms", action="store_true", help="Acknowledge upstream source terms for local acquisition")
    p_fetch.set_defaults(func=cmd_fetch)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
