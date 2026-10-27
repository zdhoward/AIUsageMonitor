"""Read-only Antigravity (Gemini) quota probe using the stored T3 login.

T3's provider status cache for the `antigravity` driver only carries the
`3p-5h` / `3p-weekly` buckets, which are the Claude & GPT shared allowance - not
Gemini. Gemini quota is available from the same read-only
`v1internal:fetchAvailableModels` POST that T3 uses when its summary has no
usable windows. `quotaInfo.remainingFraction` is a fraction REMAINING (not
used), `weeklyQuotaInfo` is optional.

This module never writes T3/agy state, prints credentials, raw responses or
request exception text. Tokens are refreshed in memory and reused until shortly
before expiry. Polling is every five minutes on success and failure. On a failed
refresh the last good accounts are returned unchanged, keeping their original
`checked_at` so the display ages them honestly.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .. import log
from ..models import Account, Window

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
QUOTA_ENDPOINTS = ("https://daily-cloudcode-pa.googleapis.com", "https://cloudcode-pa.googleapis.com")
USER_AGENT = "antigravity/hub/1.0.0 (aidev_client; os_type=windows; arch=amd64; cl=963137146)"
MAX_BODY = 512 * 1024

ANTIGRAV_NAME = "Antigrav"
ARGON_NAME = "Argon"
ARGON_MODEL = "gemini-4-argon"
ANTIGRAV_COLOR = "4285f4"
ARGON_COLOR = "9b72cb"
ANTIGRAV_UNAVAILABLE = "quota unavailable"
ARGON_UNAVAILABLE = "no independent quota"  # 20 chars: fits the device field


class QuotaError(Exception):
    """Bounded, credential-free failure with a short display-safe reason."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class Token:
    client_id: str
    client_secret: str
    refresh_token: str
    project_id: str | None


@dataclass
class TokenChoice:
    token: Token | None
    profile: str | None
    reason: str | None  # why no token, when token is None


def _iso(value) -> float | None:
    if not value:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _token_file(t3_home: Path, profile: str) -> Path:
    return t3_home / "userdata" / "providers" / "antigravity" / profile / "antigravity-acp" / "acp_token.json"


def _instances(t3_home: Path) -> dict:
    try:
        settings = json.loads((t3_home / "userdata" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    instances = settings.get("providerInstances")
    return instances if isinstance(instances, dict) else {}


def _cache_fingerprints(t3_home: Path) -> list[tuple[str, str]]:
    """(instance id, credential fingerprint) for enabled antigravity caches."""
    found = []
    for path in sorted((t3_home / "caches").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict) or doc.get("driver") != "antigravity" or not doc.get("enabled", True):
            continue
        fp = (doc.get("usageLimits") or {}).get("credentialFingerprint")
        if isinstance(fp, str) and fp:
            found.append((str(doc.get("instanceId") or path.stem), fp))
    return found


def _read_token(path: Path) -> Token | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict):
        return None
    required = (doc.get("client_id"), doc.get("client_secret"), doc.get("refresh_token"))
    if not all(isinstance(v, str) and v for v in required):
        return None
    project = doc.get("project_id")
    return Token(required[0], required[1], required[2], project if isinstance(project, str) and project else None)


def _unique(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def discover_token(t3_home: Path) -> TokenChoice:
    """Pick the configured/default Antigravity token without cross-account mixing.

    Preference order: the profile directory named by the enabled cache's
    credential fingerprint, then the configured/default instance directory, then
    a sole stored profile. More than one remaining candidate is reported as
    ambiguous instead of aggregating unrelated accounts.
    """
    base = t3_home / "userdata" / "providers" / "antigravity"
    try:
        profiles = [p.name for p in base.iterdir() if p.is_dir() and _token_file(t3_home, p.name).is_file()]
    except OSError:
        profiles = []
    if not profiles:
        return TokenChoice(None, None, "no stored login")

    instances = _instances(t3_home)
    configured = [
        iid for iid, inst in instances.items()
        if isinstance(inst, dict) and inst.get("driver") == "antigravity" and inst.get("enabled", True)
    ]
    candidates: list[str] = []
    for _iid, fp in _cache_fingerprints(t3_home):
        if fp in profiles and fp not in candidates:
            candidates.append(fp)
    for iid in configured:
        if iid in profiles and iid not in candidates:
            candidates.append(iid)
    if not candidates and "antigravity" in profiles:
        candidates.append("antigravity")
    if not candidates and len(profiles) == 1:
        candidates.append(profiles[0])
    if not candidates:
        return TokenChoice(None, None, "ambiguous account")
    if len(candidates) > 1:
        return TokenChoice(None, None, "ambiguous account")

    profile = candidates[0]
    token = _read_token(_token_file(t3_home, profile))
    if token is None:
        return TokenChoice(None, None, "unreadable login")
    return TokenChoice(token, profile, None)


def _post_json(url: str, data: bytes, headers: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            raw = resp.read(MAX_BODY + 1)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise QuotaError(f"request failed ({type(e).__name__})") from None
    if status != 200:
        raise QuotaError(f"http {status}")
    if len(raw) > MAX_BODY:
        raise QuotaError("response too large")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise QuotaError("malformed response") from None
    if not isinstance(doc, dict):
        raise QuotaError("malformed response")
    return doc


def refresh_access_token(token: Token, timeout: float) -> tuple[str, float]:
    body = urllib.parse.urlencode(
        {
            "client_id": token.client_id,
            "client_secret": token.client_secret,
            "refresh_token": token.refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode()
    doc = _post_json(TOKEN_ENDPOINT, body, {"Content-Type": "application/x-www-form-urlencoded"}, timeout)
    access = doc.get("access_token")
    expires = doc.get("expires_in")
    if not isinstance(access, str) or not access or not isinstance(expires, (int, float)) or isinstance(expires, bool):
        raise QuotaError("malformed token response")
    return access, time.time() + float(expires)


def fetch_models(token: Token, access_token: str, timeout: float) -> dict:
    """POST fetchAvailableModels, returning the decoded model map only."""
    body = json.dumps({"project": token.project_id} if token.project_id else {}).encode()
    last: QuotaError | None = None
    for base in QUOTA_ENDPOINTS:
        try:
            doc = _post_json(
                f"{base}/v1internal:fetchAvailableModels",
                body,
                {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                },
                timeout,
            )
        except QuotaError as e:
            last = e
            continue
        models = doc.get("models")
        if isinstance(models, dict) and models:
            return models
        last = QuotaError("no models reported")
    raise last or QuotaError("no models reported")


def _family(model_id: str, model: dict) -> str | None:
    provider = model.get("modelProvider")
    if provider == "MODEL_PROVIDER_GOOGLE" or model_id.startswith("gemini-"):
        return "gemini"
    if provider == "MODEL_PROVIDER_ANTHROPIC" or model_id.startswith("claude-"):
        return "claude"
    if provider == "MODEL_PROVIDER_OPENAI" or model_id.startswith("gpt-"):
        return "gpt"
    return None


def fraction_to_used(fraction) -> float | None:
    """quotaInfo.remainingFraction is remaining; the display works in USED percent."""
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
        return None
    if not math.isfinite(fraction):
        return None
    return (1.0 - min(max(float(fraction), 0.0), 1.0)) * 100.0


def _quota_window(window_id: str, kind: str, label: str, quota, mins: int | None) -> Window | None:
    if not isinstance(quota, dict):
        return None
    used = fraction_to_used(quota.get("remainingFraction"))
    if used is None:
        return None
    return Window(
        id=window_id,
        kind=kind,
        label=label,
        used_percent=used,
        resets_at=_iso(quota.get("resetTime")),
        window_mins=mins,
    )


def _clean_models(models) -> dict:
    if not isinstance(models, dict):
        raise QuotaError("malformed models")
    return {mid: m for mid, m in models.items() if isinstance(mid, str) and isinstance(m, dict)}


def _gemini_windows(models: dict) -> list[Window]:
    """Worst reported Gemini model quota per window; never family/3p substitution."""
    session: list[Window] = []
    weekly: list[Window] = []
    for mid, model in models.items():
        if mid == ARGON_MODEL or _family(mid, model) != "gemini":
            continue
        w = _quota_window(f"{mid}-quota", "session", "5h", model.get("quotaInfo"), 300)
        if w:
            session.append(w)
        w = _quota_window(f"{mid}-weekly", "weekly", "7d", model.get("weeklyQuotaInfo"), 10080)
        if w:
            weekly.append(w)
    windows: list[Window] = []
    if session:
        worst = max(session, key=lambda w: w.used_percent or 0.0)
        windows.append(Window("antigravity-5h", "session", "5h", worst.used_percent, worst.resets_at, 300))
    if weekly:
        worst = max(weekly, key=lambda w: w.used_percent or 0.0)
        windows.append(Window("antigravity-7d", "weekly", "7d", worst.used_percent, worst.resets_at, 10080))
    return windows


def _argon_windows(models: dict) -> list[Window]:
    """Only the distinct gemini-4-argon model; family or 3p numbers never stand in."""
    model = models.get(ARGON_MODEL)
    if not isinstance(model, dict):
        return []
    windows: list[Window] = []
    primary = _quota_window(f"{ARGON_MODEL}-quota", "session", "5h", model.get("quotaInfo"), 300)
    if primary:
        windows.append(primary)
    weekly = _quota_window(f"{ARGON_MODEL}-weekly", "weekly", "7d", model.get("weeklyQuotaInfo"), 10080)
    if weekly:
        windows.append(weekly)
    return windows


def accounts_from_models(models, now: float) -> list[Account]:
    """Build the stable Antigrav and Argon accounts from one model map."""
    clean = _clean_models(models)
    antigrav = Account(
        instance_id="antigravity_direct",
        name=ANTIGRAV_NAME,
        driver="antigravity",
        plan=None,
        color=ANTIGRAV_COLOR,
        source="antigravity_direct",
    )
    argon = Account(
        instance_id="antigravity_argon",
        name=ARGON_NAME,
        driver="antigravity",
        plan=None,
        color=ARGON_COLOR,
        source="antigravity_direct",
    )
    antigrav.windows = _gemini_windows(clean)
    if antigrav.windows:
        antigrav.checked_at = now
    else:
        antigrav.unavailable = "no Gemini quota"
    argon.windows = _argon_windows(clean)
    if argon.windows:
        argon.checked_at = now
    else:
        argon.unavailable = ARGON_UNAVAILABLE
    return [antigrav, argon]


def placeholder_accounts(reason: str) -> list[Account]:
    """Stable cells even before the first successful probe."""
    return [
        Account("antigravity_direct", ANTIGRAV_NAME, "antigravity", None, ANTIGRAV_COLOR,
                unavailable=reason, source="antigravity_direct"),
        Account("antigravity_argon", ARGON_NAME, "antigravity", None, ARGON_COLOR,
                unavailable=ARGON_UNAVAILABLE, source="antigravity_direct"),
    ]


def _copy(accounts: list[Account]) -> list[Account]:
    return [
        Account(
            instance_id=a.instance_id,
            name=a.name,
            driver=a.driver,
            plan=a.plan,
            color=a.color,
            windows=[Window(w.id, w.kind, w.label, w.used_percent, w.resets_at, w.window_mins) for w in a.windows],
            checked_at=a.checked_at,
            source=a.source,
            unavailable=a.unavailable,
            reset_credits=a.reset_credits,
        )
        for a in accounts
    ]


class AntigravityReader:
    """Five-minute, guarded direct Gemini quota source with last-good retention."""

    def __init__(self, t3_home: Path, refresh_s: float = 300.0, timeout_s: float = 8.0):
        self.t3_home = t3_home
        self.refresh_s = max(300.0, refresh_s)
        self.timeout_s = min(30.0, max(1.0, timeout_s))
        self._next = 0.0
        self._good: list[Account] | None = None
        self._access: str | None = None
        self._access_expires = 0.0
        self._profile: str | None = None
        self._reason: str | None = None

    def read(self, now: float) -> list[Account]:
        if now < self._next:
            return self._current()
        self._next = now + self.refresh_s
        try:
            accounts = self._fetch(now)
        except QuotaError as e:
            self._reason = e.reason
            log.warn("antigravity.failed", reason=e.reason)
            return self._current()
        except Exception as e:  # a broken probe must never blank the account cells
            self._reason = "probe failed"
            log.warn("antigravity.failed", err=type(e).__name__)
            return self._current()
        self._good = accounts
        self._reason = None
        log.event("antigravity.probe", accounts=len(accounts), windows=sum(len(a.windows) for a in accounts))
        return _copy(accounts)

    def _current(self) -> list[Account]:
        if self._good is not None:
            return _copy(self._good)  # original checked_at stays untouched
        return placeholder_accounts(self._reason or ANTIGRAV_UNAVAILABLE)

    def _access_token(self, token: Token, now: float) -> str:
        if self._access and now < self._access_expires - 60:
            return self._access
        access, expires = refresh_access_token(token, self.timeout_s)
        self._access, self._access_expires = access, expires
        return access

    def _fetch(self, now: float) -> list[Account]:
        choice = discover_token(self.t3_home)
        if choice.token is None:
            raise QuotaError(choice.reason or "no stored login")
        if choice.profile != self._profile:  # never reuse another profile's token
            self._access, self._access_expires, self._profile = None, 0.0, choice.profile
            self._good = None
        access = self._access_token(choice.token, now)
        models = fetch_models(choice.token, access, self.timeout_s)
        return accounts_from_models(models, now)
