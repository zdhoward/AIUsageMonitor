"""CPAMC (CLIProxyAPI) proxy-group quota for the Proxy home view.

Reads accounts from `GET /v0/management/auth-files` and live usage per active
account through `POST /v0/management/api-call`, driven by the provider profiles
in `aimon/profiles/*.json` (see that README). Quota is pooled per proxy group:
sum(remaining) / (100 * accounts). The result is the compact `proxy` serial
line described in docs/PROTOCOL.md.

The management key comes from CPAMC_MANAGEMENT_KEY or the gitignored
`service/.cpamc.env`. Keys, tokens, response bodies and account emails are
never logged.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from .. import log

BASE = "http://127.0.0.1:8317"
PROFILE_DIR = Path(__file__).resolve().parents[1] / "profiles"
ENV_FILE = Path(__file__).resolve().parents[2] / ".cpamc.env"
ACCOUNTS_EVERY_S = 30.0
LIVE_EVERY_S = 300.0
# Display order; the double-wide multi tile packs onto row 2.
ORDER = ["claude", "codex", "xai", "antigravity"]
NAMES = {"claude": "Claude", "codex": "Codex", "xai": "xAI", "antigravity": "Antigrav"}


def load_key() -> str:
    key = os.environ.get("CPAMC_MANAGEMENT_KEY", "")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("CPAMC_MANAGEMENT_KEY="):
                key = line.split("=", 1)[1].strip()
    return key


def load_profiles(directory: Path = PROFILE_DIR) -> dict:
    out = {}
    for p in sorted(directory.glob("*.json")):
        try:
            prof = json.loads(p.read_text(encoding="utf-8"))
            out[prof["provider"]] = prof
        except (OSError, ValueError, KeyError):
            log.warn("cpamc.bad_profile", file=p.name)
    return out


def _get(obj, path: str | None):
    if obj is None or not path:
        return None
    for part in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def _select(body, path: str, match: dict | None):
    """Resolve a dotted path where `name[*]` walks every list item."""
    nodes = [body]
    for part in path.split("."):
        nxt = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if part.endswith("[*]"):
                v = n.get(part[:-3])
                if isinstance(v, list):
                    nxt.extend(v)
            elif part in n:
                nxt.append(n[part])
        nodes = nxt
    if match:
        nodes = [n for n in nodes if isinstance(n, dict) and all(n.get(k) == v for k, v in match.items())]
    return nodes[0] if nodes else None


def _epoch(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    if s.isdigit():
        return float(s)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def label_for(seconds: float) -> str:
    if seconds <= 0:
        return "?"
    if seconds < 86400:
        return f"{round(seconds / 3600)}h"
    return f"{round(seconds / 86400)}d"


def read_windows(profile: dict, body) -> list[dict]:
    """Profile + one account's response -> [{pool, label, rem (0-100 or None), reset, len}]."""
    out = []
    for w in profile.get("windows", []):
        node = _select(body, w["path"], w.get("match"))
        if not isinstance(node, dict):
            continue
        if w.get("skip_if") and node.get(w["skip_if"]):
            continue  # e.g. a paused 5h bucket while the weekly is exhausted
        length = w.get("length_s")
        length = float(_get(node, length) or 0) if isinstance(length, str) else float(length or 0)
        if w.get("remaining"):
            raw = _get(node, w["remaining"])
            rem = float(raw or 0) * (100 / w.get("scale", 1))  # a missing fraction means 0
        elif w.get("used"):
            raw = _get(node, w["used"])
            rem = None if raw is None else 100 - float(raw) * (100 / w.get("scale", 100))
        else:
            rem = None
        text = ""
        if w.get("used_text"):
            used = _get(node, w["used_text"])
            limit = float(_get(node, w.get("limit")) or 0)
            if used is not None and limit > 0:
                rem = 100 - float(used) / limit * 100
            elif used is not None:
                text = w.get("text_fmt", "{}").format(used)  # no limit reported: raw figure
        if length <= 0 and not w.get("label"):
            continue  # empty window (e.g. a Free plan's unused secondary)
        out.append({"pool": w["pool"], "label": w.get("label") or label_for(length),
                    "rem": None if rem is None else max(0.0, min(100.0, rem)),
                    "reset": _epoch(_get(node, w.get("reset"))), "len": length, "text": text})
    return out


def header_windows(provider: str, signals: dict) -> list[dict]:
    """Fallback: rate-limit headers CPAMC observed on the account's last request."""
    out = []
    if provider == "claude":
        for lab, key, ln in (("5h", "5h", 18000), ("7d", "7d", 604800)):
            u = signals.get(f"Anthropic-Ratelimit-Unified-{key}-Utilization")
            if u is not None:
                out.append({"pool": "main", "label": lab, "rem": 100 - float(u) * 100,
                            "reset": _epoch(signals.get(f"Anthropic-Ratelimit-Unified-{key}-Reset")), "len": ln})
    elif provider == "codex":
        for side in ("Primary", "Secondary"):
            mins = float(signals.get(f"X-Codex-{side}-Window-Minutes") or 0)
            if mins > 0:
                out.append({"pool": "main", "label": label_for(mins * 60),
                            "rem": 100 - float(signals.get(f"X-Codex-{side}-Used-Percent") or 0),
                            "reset": _epoch(signals.get(f"X-Codex-{side}-Reset-At")), "len": mins * 60})
    return out


def needs_attention(acc: dict) -> bool:
    if acc.get("disabled"):
        return False
    msg = str(acc.get("status_message") or "").lower()
    if any(k in msg for k in ("rate_limit", "rate limit", "quota", "resource_exhausted", "429")):
        return False  # exhausted quota resolves by waiting; not actionable
    return (acc.get("status") not in ("active", None) or bool(acc.get("unavailable"))
            or bool(msg))


def pool_groups(accounts: list[dict], live: dict, profiles: dict, now: float) -> list[dict]:
    """accounts: auth-files entries. live: auth_index -> windows (or None on failure)."""
    by_provider: dict[str, list] = {}
    for a in accounts:
        if not a.get("disabled"):
            by_provider.setdefault(a.get("provider", "?"), []).append(a)
    order = [p for p in ORDER if p in by_provider] + sorted(p for p in by_provider if p not in ORDER)
    groups = []
    for prov in order:
        accs = by_provider[prov]
        prof = profiles.get(prov, {})
        tile = prof.get("tile", {})
        pools = tile.get("pools") or [{"id": "main", "label": NAMES.get(prov, prov.title())}]
        attn = any(needs_attention(a) or live.get(a.get("auth_index"), {}).get("auth_failed") for a in accs)
        per_acc = []
        for a in accs:
            entry = live.get(a.get("auth_index")) or {}
            wins = entry.get("windows")
            if wins is None:
                wins = header_windows(prov, (a.get("quota") or {}).get("signals") or {})
            # Quota cooldown on an account without readings: treat as empty until retry_at.
            if not wins:
                cds = [c for c in a.get("cooldowns") or [] if c.get("reason") == "quota"]
                if cds:
                    wins = [{"pool": pools[0]["id"], "label": "7d", "rem": 0.0,
                             "reset": min(_epoch(c.get("retry_at")) for c in cds), "len": 604800}]
            per_acc.append(wins)
        out_pools = []
        for pl in pools[:3]:
            labels = []
            for wins in per_acc:
                for w in wins:
                    if w["pool"] == pl["id"] and (w["label"], w["len"]) not in labels:
                        labels.append((w["label"], w["len"]))
            labels.sort(key=lambda x: x[1])
            ws = []
            for lab, _ in labels[:2]:
                rems, resets, known, texts = [], [], False, []
                for wins in per_acc:
                    hit = next((w for w in wins if w["pool"] == pl["id"] and w["label"] == lab), None)
                    if hit is None or hit["rem"] is None:
                        if hit and hit.get("text"):
                            texts.append(hit["text"])
                        if hit and hit["reset"] > now:
                            resets.append(hit["reset"])
                        rems.append(None)
                        continue
                    known = True
                    if hit["reset"] and hit["reset"] <= now:
                        rems.append(100.0)  # past reset: refilled
                    else:
                        rems.append(hit["rem"])
                        if hit["reset"] > now:
                            resets.append(hit["reset"])
                vals = [r for r in rems if r is not None]
                r = round(sum(vals) / len(vals)) if known and vals else -1
                win = {"l": lab, "r": r, "z": int(min(resets)) if resets else 0}
                if r < 0 and len(texts) == 1:
                    win["v"] = texts[0][:8]  # raw figure for a provider without a limit
                ws.append(win)
            out_pools.append({"l": pl["label"], "w": ws})
        groups.append({"n": NAMES.get(prov, prov.title()), "c": len(accs), "a": int(bool(attn)),
                       "ly": "m" if tile.get("layout") == "multi" else "r", "p": out_pools})
    return groups[:6]


class CpamcSource:
    """Background poller. `line()` returns the latest `proxy` serial message."""

    def __init__(self, base: str = BASE):
        self.base = base
        self.key = load_key()
        self.profiles = load_profiles()
        self._accounts: list[dict] = []
        self._live: dict = {}
        self._live_at: dict = {}
        self._ok_at = 0.0
        self._up = False
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def _call(self, method: str, path: str, body: dict | None = None, timeout: float = 30):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def _live_one(self, acc: dict, prof: dict) -> dict:
        req = prof["request"]
        data = req.get("data")
        if data:
            data = data.replace("{project_id}", acc.get("project_id") or "")
        for url in [req["url"], *req.get("fallback_urls", [])]:
            payload = {"auth_index": acc["auth_index"], "method": req["method"], "url": url, "header": req["header"]}
            if data:
                payload["data"] = data
            try:
                out = self._call("POST", "/v0/management/api-call", payload)
            except Exception as e:
                log.warn("cpamc.live_error", provider=acc.get("provider"), err=type(e).__name__)
                continue
            status = out.get("status_code")
            if status in (401, 403):
                return {"windows": None, "auth_failed": True}
            if status != 200:
                continue
            body = out.get("body")
            try:
                body = json.loads(body) if isinstance(body, str) else body
            except ValueError:
                continue
            wins = read_windows(prof, body)
            if wins:
                return {"windows": wins}
        return {"windows": None}

    def poll_once(self) -> None:
        now = time.time()
        try:
            accounts = self._call("GET", "/v0/management/auth-files", timeout=10).get("files", [])
            up = True
        except Exception as e:
            log.warn("cpamc.unreachable", err=type(e).__name__)
            with self._lock:
                self._up = False
            return
        live = dict(self._live)
        for a in accounts:
            prof = self.profiles.get(a.get("provider"))
            idx = a.get("auth_index")
            if a.get("disabled") or not prof or not idx:
                continue
            if now - self._live_at.get(idx, 0) >= LIVE_EVERY_S:
                res = self._live_one(a, prof)
                if res.get("windows") is None and not res.get("auth_failed") and idx in live:
                    res = live[idx]  # keep the last good reading
                live[idx] = res
                self._live_at[idx] = now
        with self._lock:
            self._accounts, self._live, self._up, self._ok_at = accounts, live, up, now
        log.event("cpamc.poll", accounts=len(accounts))

    def run(self) -> None:
        if not self.key:
            log.warn("cpamc.disabled", reason="no management key")
            return
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception as e:  # never let the thread die
                log.warn("cpamc.poll_error", err=type(e).__name__)
            self._stop.wait(ACCOUNTS_EVERY_S)

    def stop(self) -> None:
        self._stop.set()

    def line(self) -> dict | None:
        if not self.key:
            return None
        now = time.time()
        with self._lock:
            if not self._ok_at and not self._accounts:
                return {"t": "proxy", "ts": int(now), "up": 0, "age": 0, "attn": 1, "g": []}
            groups = pool_groups(self._accounts, self._live, self.profiles, now)
            up = self._up
            age = int(now - self._ok_at) if self._ok_at else 0
        attn = (not up) or any(g["a"] for g in groups)
        return {"t": "proxy", "ts": int(now), "up": int(up), "age": age, "attn": int(attn), "g": groups}
