"""Pure parser for the Claude reset-credit inventory (``cedar_ember`` block).

Reads only; never consumes a grant. Returns ``{"rc": int, "rx": int}`` where
rc is the available reset count (-1 unknown) and rx the earliest known expiry
epoch among counted grants (0 if none known). No identifiers are returned.
"""

import math
import re
from datetime import datetime, timezone

UNKNOWN = {"rc": -1, "rx": 0}

_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


def _unknown():
    return dict(UNKNOWN)


def _parse_ts(value):
    """RFC3339 with explicit timezone -> epoch float; None if invalid."""
    if not isinstance(value, str) or not _RFC3339.match(value):
        return None
    text = value.replace("t", "T")
    if text[-1] in "Zz":
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    ts = dt.astimezone(timezone.utc).timestamp()
    return ts if math.isfinite(ts) else None


def parse_inventory(block, now):
    try:
        return _parse(block, now)
    except Exception:  # unreadable data must never look like zero
        return _unknown()


def _parse(block, now):
    if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
        return _unknown()
    if not isinstance(block, dict):
        return _unknown()
    eligible = block.get("eligible")
    grants = block.get("grants")
    if not isinstance(eligible, bool) or not isinstance(grants, list):
        return _unknown()
    if not eligible:
        return {"rc": 0, "rx": 0} if not grants else _unknown()

    count = 0
    earliest = None
    for grant in grants:
        if not isinstance(grant, dict):
            return _unknown()
        left = grant.get("resets_left")
        if isinstance(left, bool) or not isinstance(left, int) or left < 0:
            return _unknown()
        usable = grant.get("usable_now")
        if not isinstance(usable, bool):
            return _unknown()
        paused = grant.get("paused")
        if paused is not None and not isinstance(paused, bool):
            return _unknown()
        expiry = None
        ends_at = grant.get("ends_at")
        if ends_at is not None:
            expiry = _parse_ts(ends_at)
            if expiry is None:
                return _unknown()
        if left <= 0 or not usable or paused is True:
            continue
        if expiry is not None and expiry <= now:
            continue
        count += left
        if expiry is not None and (earliest is None or expiry < earliest):
            earliest = expiry

    rx = 0 if earliest is None else int(earliest)
    return {"rc": count, "rx": rx}
