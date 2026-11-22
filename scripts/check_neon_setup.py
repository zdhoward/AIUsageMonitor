"""Check local setup structure; a pass does not prove API availability or rule semantics."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse

OLD_PERSONA = "you are a coding agent running in the codex cli"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only check for isolated Neon Codex configuration."
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home() / ".codex_cpamc_gemini",
        help="Codex home directory to inspect.",
    )
    return parser.parse_args(argv)


def is_valid_http_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def check_home(home: Path) -> tuple[dict[str, object], int]:
    resolved_home = home.expanduser()
    config_path = resolved_home / "config.toml"
    auth_json_exists = (resolved_home / "auth.json").is_file()

    try:
        with config_path.open("rb") as handle:
            config = tomllib.load(handle)
    except Exception as exc:
        payload: dict[str, object] = {
            "ok": False,
            "default_model": None,
            "config_valid": False,
            "auth_json_exists": auth_json_exists,
            "error_type": type(exc).__name__,
        }
        return payload, 1

    raw_model = config.get("model")
    default_model = raw_model if isinstance(raw_model, str) else None
    model_is_gemini = bool(default_model and default_model.startswith("gemini-"))

    provider_name = config.get("model_provider")
    providers = config.get("model_providers")
    provider_cfg = (
        providers.get(provider_name)
        if isinstance(provider_name, str) and provider_name and isinstance(providers, dict)
        else None
    )
    provider_exists = isinstance(provider_cfg, dict)
    wire_api_responses = bool(provider_exists and provider_cfg.get("wire_api") == "responses")
    base_url_valid = bool(provider_exists and is_valid_http_url(provider_cfg.get("base_url")))

    instructions_raw = config.get("model_instructions_file")
    instructions_file_exists = False
    instructions_opening_clean = False
    instructions_rules_present = False
    error_type: str | None = None

    if isinstance(instructions_raw, str) and instructions_raw.strip():
        instructions_path = Path(instructions_raw.strip()).expanduser()
        if not instructions_path.is_absolute():
            instructions_path = resolved_home / instructions_path
        instructions_file_exists = instructions_path.is_file()
        if instructions_file_exists:
            try:
                text = instructions_path.read_text(encoding="utf-8")
            except Exception as exc:
                error_type = type(exc).__name__
            else:
                paragraphs = [
                    paragraph.strip()
                    for paragraph in re.split(r"\r?\n\s*\r?\n", text.strip())
                    if paragraph.strip()
                ]
                if paragraphs:
                    opening = paragraphs[0]
                    instructions_opening_clean = OLD_PERSONA not in opening.lower()
                    remaining = "\n\n".join(paragraphs[1:])
                    has_headings = any(
                        line.lstrip().startswith("#") for line in remaining.splitlines()
                    )
                    instructions_rules_present = (
                        len(paragraphs) >= 2 and len(remaining) >= 200 and has_headings
                    )

    ok = all(
        (
            model_is_gemini,
            provider_exists,
            wire_api_responses,
            base_url_valid,
            instructions_file_exists,
            instructions_opening_clean,
            instructions_rules_present,
            auth_json_exists,
            error_type is None,
        )
    )

    payload = {
        "ok": ok,
        "default_model": default_model,
        "config_valid": True,
        "model_is_gemini": model_is_gemini,
        "provider_exists": provider_exists,
        "wire_api_responses": wire_api_responses,
        "base_url_valid": base_url_valid,
        "instructions_file_exists": instructions_file_exists,
        "instructions_opening_clean": instructions_opening_clean,
        "instructions_rules_present": instructions_rules_present,
        "auth_json_exists": auth_json_exists,
    }
    if error_type is not None:
        payload["error_type"] = error_type
    return payload, 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload, exit_code = check_home(args.home)
    print(json.dumps(payload, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
