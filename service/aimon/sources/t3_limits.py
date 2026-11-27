"""Subscription windows from T3's provider status cache (~/.t3/caches/<instance>.json).

T3 writes these files when it refreshes provider status, including `usageLimits` from
Anthropic's and OpenAI's usage endpoints. Reading them needs no credentials.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .. import log
from ..models import Account, Window

QUOTA_DRIVERS = {"claudeAgent", "codex", "antigravity"}
DEFAULT_NAMES = {"claudeAgent": "Claude", "codex": "Codex", "antigravity": "Gemini"}
DEFAULT_COLORS = {"claudeAgent": "d97757", "codex": "10a37f", "antigravity": "4285f4"}


def parse_iso(value) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def window_label(kind: str, mins: int | None, fallback: str) -> str:
    if mins:
        if mins % 1440 == 0:
            return f"{mins // 1440}d"
        if mins % 60 == 0:
            return f"{mins // 60}h"
    return {"session": "5h", "weekly": "7d"}.get(kind, (fallback or "?")[:3])


def short_plan(label: str | None) -> str | None:
    if not label:
        return None
    for word in ("Max 20x", "Max 5x", "Max", "Pro", "Plus", "Team", "Enterprise", "Free"):
        if word.lower() in label.lower():
            return word
    return label.split()[0][:8]


def parse_cache(doc: dict, instance_id: str, display_names: dict[str, str]) -> Account | None:
    driver = doc.get("driver") or ""
    if driver not in QUOTA_DRIVERS or not doc.get("enabled", True):
        return None
    name = display_names.get(instance_id) or doc.get("displayName") or DEFAULT_NAMES.get(driver, instance_id)
    color = (doc.get("accentColor") or "").lstrip("#") or DEFAULT_COLORS.get(driver)
    acct = Account(
        instance_id=instance_id,
        name=name,
        driver=driver,
        plan=short_plan((doc.get("auth") or {}).get("label")),
        color=color,
    )
    auth_status = (doc.get("auth") or {}).get("status")
    limits = doc.get("usageLimits")
    if not isinstance(limits, dict):
        acct.unavailable = "signed out" if auth_status == "unauthenticated" else "no limits reported"
        return acct
    acct.checked_at = parse_iso(limits.get("checkedAt"))
    credits = (limits.get("resetCredits") or {}).get("availableCount")
    if isinstance(credits, int):
        acct.reset_credits = credits
    for w in limits.get("windows") or []:
        if not isinstance(w, dict):
            continue
        used = w.get("usedPercent")
        mins = w.get("windowDurationMins")
        acct.windows.append(
            Window(
                id=str(w.get("id", "")),
                kind=str(w.get("kind", "other")),
                label=window_label(str(w.get("kind", "")), int(mins) if isinstance(mins, (int, float)) else None, str(w.get("label", ""))),
                used_percent=float(used) if isinstance(used, (int, float)) else None,
                resets_at=parse_iso(w.get("resetsAt")),
                window_mins=int(mins) if isinstance(mins, (int, float)) else None,
            )
        )
    if not acct.windows:
        reason = (limits.get("unavailable") or {}).get("reason")
        acct.unavailable = reason or "no windows reported"
    return acct


def _read_instances(t3_home: Path) -> dict[str, dict]:
    try:
        settings = json.loads((t3_home / "userdata" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    raw = settings.get("providerInstances")
    if not isinstance(raw, dict):
        return {}
    return {iid: inst for iid, inst in raw.items() if isinstance(inst, dict)}


def _is_proxy_instance(inst: dict) -> bool:
    env = inst.get("environment")
    if isinstance(env, dict):
        return any(str(k).endswith("_BASE_URL") and bool(v) for k, v in env.items())
    if isinstance(env, list):
        for item in env:
            if not isinstance(item, dict):
                continue
            key = item.get("name") or item.get("key") or ""
            if str(key).endswith("_BASE_URL") and item.get("value"):
                return True
    return False


def read_display_names(t3_home: Path) -> dict[str, str]:
    return {
        iid: inst["displayName"]
        for iid, inst in _read_instances(t3_home).items()
        if inst.get("displayName")
    }


def read_accounts(t3_home: Path) -> list[Account]:
    instances = _read_instances(t3_home)
    names = {iid: inst["displayName"] for iid, inst in instances.items() if inst.get("displayName")}
    accounts = []
    for path in sorted((t3_home / "caches").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            log.warn("t3_limits.bad_cache", file=path.name, err=type(e).__name__)
            continue
        if not isinstance(doc, dict):
            continue
        iid = doc.get("instanceId") or path.stem
        if instances:
            inst = instances.get(iid)
            if inst is None or not inst.get("enabled", True) or _is_proxy_instance(inst):
                continue
        acct = parse_cache(doc, iid, names)
        if acct:
            accounts.append(acct)
    return accounts
