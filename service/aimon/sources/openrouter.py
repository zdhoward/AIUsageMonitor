"""OpenRouter key status: free-model daily request allowance and actual spend.

Calls GET /api/v1/key with the key already configured on this PC (env OPENROUTER_API_KEY,
else OpenCode's auth.json). It's a status call that sends no prompt and uses no model
quota. The key is never logged or forwarded.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

URL = "https://openrouter.ai/api/v1/key"


@dataclass
class OpenRouterStatus:
    checked_at: float
    error: str | None = None
    free_used: int | None = None
    free_limit: int | None = None
    usd_daily: float | None = None
    usd_monthly: float | None = None
    budget_remaining: float | None = None
    free_tier: bool | None = None


def find_key() -> str | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    auth = Path.home() / ".local" / "share" / "opencode" / "auth.json"
    try:
        return (json.loads(auth.read_text(encoding="utf-8")).get("openrouter") or {}).get("key")
    except (OSError, ValueError):
        return None


def parse(data: dict, now: float) -> OpenRouterStatus:
    free = data.get("free_model_daily_requests") or {}
    budget = data.get("effective_budget") or {}
    remaining = budget.get("remaining_usd", data.get("limit_remaining"))
    return OpenRouterStatus(
        checked_at=now,
        free_used=free.get("used"),
        free_limit=free.get("limit"),
        usd_daily=data.get("usage_daily"),
        usd_monthly=data.get("usage_monthly"),
        budget_remaining=float(remaining) if isinstance(remaining, (int, float)) else None,
        free_tier=data.get("is_free_tier"),
    )


def fetch(now: float, timeout: float = 10.0) -> OpenRouterStatus:
    key = find_key()
    if not key:
        return OpenRouterStatus(checked_at=now, error="no key")
    req = urllib.request.Request(URL, headers={"Authorization": f"Bearer {key}", "User-Agent": "aimon/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        return OpenRouterStatus(checked_at=now, error="key rejected" if e.code in (401, 403) else f"http {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError):
        return OpenRouterStatus(checked_at=now, error="offline")
    except ValueError:
        return OpenRouterStatus(checked_at=now, error="bad response")
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return OpenRouterStatus(checked_at=now, error="bad response")
    return parse(data, now)
