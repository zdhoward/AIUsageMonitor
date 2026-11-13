"""CPAMC (CLIProxyAPI) proxy-group quota for the Proxy home view.

Reads accounts from `GET /v0/management/auth-files` and live usage per active
account through `POST /v0/management/api-call`, driven by the provider profiles
in `aimon/profiles/*.json` (see that README). Quota is pooled per proxy group:
sum(remaining) / (100 * accounts). The result is the compact `proxy` serial
line described in docs/PROTOCOL.md.

The management key (CPAMC_MANAGEMENT_KEY) and an optional address override
(CPAMC_URL, default http://127.0.0.1:8317) come from the environment or the
gitignored `service/.cpamc.env`. Keys, tokens, response bodies and account emails are
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
ACCOUNTS_EVERY_S = 5.0  # local auth-files call only; live quota probes stay on LIVE_EVERY_S
LIVE_EVERY_S = 300.0
# Display order; the double-wide multi tile packs onto row 2.
ORDER = ["claude", "codex", "xai", "antigravity"]
NAMES = {"claude": "Claude", "codex": "Codex", "xai": "xAI", "antigravity": "Antigrav"}


def _setting(name: str) -> str:
    """Environment variable first, then the gitignored `service/.cpamc.env`."""
    val = os.environ.get(name, "")
    if not val and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                val = line.split("=", 1)[1].strip()
    return val


def load_key() -> str:
    return _setting("CPAMC_MANAGEMENT_KEY")


def load_base() -> str:
    """CPAMC address. Set CPAMC_URL (env or `.cpamc.env`) when it is not on this PC."""
    return (_setting("CPAMC_URL") or BASE).rstrip("/")


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
            rem = None if raw is None else float(raw) * (100 / w.get("scale", 1))
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
            used = signals.get(f"X-Codex-{side}-Used-Percent")
            if mins > 0:
                out.append({"pool": "main", "label": label_for(mins * 60),
                            "rem": None if used is None else 100 - float(used),
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


def _exhaust_short_windows(wins: list[dict]) -> list[dict]:
    """A pool whose 7d window has 0% left cannot use its 5h window either."""
    dead = {w["pool"] for w in wins if w["label"] in ("7d", "weekly") and w["rem"] is not None and w["rem"] <= 0}
    if not dead:
        return wins
    return [dict(w, rem=0.0) if w["pool"] in dead and w["label"] in ("5h", "session") else w for w in wins]


def _pct(rem: float) -> int:
    """Whole percent left. Any quota left shows at least 1%, so the display never reads a
    usable window (e.g. 0.41%) as a 0% cooldown; only a true 0 is exhausted."""
    return 1 if 0 < rem < 1 else round(rem)


def apply_cooldowns(wins: list[dict], cooldowns, pool_map: dict, now: float) -> list[dict]:
    """An active quota cooldown on a model means that pool is exhausted, whatever the quota
    endpoint says (Google reports 100% for Argon while CPAMC holds a 429 cooldown)."""
    hit = {}
    for c in cooldowns or []:
        if c.get("reason") != "quota":
            continue
        until = _epoch(c.get("retry_at"))
        if until <= now:
            continue
        for needle, pool in (pool_map or {}).items():
            if needle in str(c.get("model_key") or ""):
                hit[pool] = max(hit.get(pool, 0), until)
    if not hit:
        return wins
    return [dict(w, rem=0.0, reset=max(w.get("reset") or 0, hit[w["pool"]])) if w["pool"] in hit else w
            for w in wins]


def pool_groups(accounts: list[dict], live: dict, profiles: dict, now: float) -> list[dict]:
    """accounts: auth-files entries. live: auth_index -> windows (or None on failure)."""
    by_provider: dict[str, list] = {}
    for a in accounts:
        if not a.get("disabled") and not profiles.get(a.get("provider"), {}).get("hidden"):
            by_provider.setdefault(a.get("provider", "?"), []).append(a)
    order = [p for p in ORDER if p in by_provider] + sorted(p for p in by_provider if p not in ORDER)
    groups = []
    for prov in order:
        # auth_index is an opaque CPAMC identifier. Never send it to the display.
        accs = sorted(by_provider[prov], key=lambda a: str(a.get("auth_index") or a.get("id") or ""))
        prof = profiles.get(prov, {})
        tile = prof.get("tile", {})
        pools = tile.get("pools") or [{"id": "main", "label": NAMES.get(prov, prov.title())}]
        attn = any(
            entry.get("auth_failed") or (needs_attention(a) and not entry.get("probe_ok"))
            for a in accs for entry in [live.get(a.get("auth_index")) or {}]
        )
        per_acc = []
        for a in accs:
            entry = live.get(a.get("auth_index")) or {}
            wins = entry.get("windows")
            if wins is None:
                wins = header_windows(prov, (a.get("quota") or {}).get("signals") or {})
            wins = apply_cooldowns(wins or [], a.get("cooldowns"), prof.get("cooldown_pools"), now)
            per_acc.append(_exhaust_short_windows(wins))
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
                rems, resets, known, texts, detail = [], [], False, [], []
                for wins in per_acc:
                    hit = next((w for w in wins if w["pool"] == pl["id"] and w["label"] == lab), None)
                    detail.append([_pct(hit["rem"]) if hit and hit["rem"] is not None else -1,
                                   int(hit["reset"]) if hit and hit["reset"] else 0])
                    if hit is None or hit["rem"] is None:
                        if hit and hit.get("text"):
                            texts.append(hit["text"])
                        if hit and hit["reset"] > now:
                            resets.append(hit["reset"])
                        rems.append(None)
                        continue
                    known = True
                    rems.append(hit["rem"])
                    if hit["reset"] > now:
                        resets.append(hit["reset"])
                vals = [r for r in rems if r is not None]
                r = _pct(sum(vals) / len(vals)) if known and vals else -1
                win = {"l": lab, "r": r, "z": int(min(resets)) if resets else 0}
                if len(accs) <= 8:
                    win["q"] = detail
                if r < 0 and len(texts) == 1:
                    win["v"] = texts[0][:8]  # raw figure for a provider without a limit
                ws.append(win)
            out_pools.append({"l": pl["label"], "w": ws})
        group = {"n": NAMES.get(prov, prov.title()), "c": len(accs), "a": int(bool(attn)),
                 "ly": "m" if tile.get("layout") == "multi" else "r", "p": out_pools}
        # Banked manual resets per account, in sector order; -1 unknown.
        credits = [(live.get(a.get("auth_index")) or {}).get("rc", -1) for a in accs]
        if len(accs) <= 8 and any(c >= 0 for c in credits):
            group["rc"] = credits
            expiry = [int((live.get(a.get("auth_index")) or {}).get("rx") or 0) for a in accs]
            if any(expiry):
                group["rx"] = expiry  # soonest banked-reset expiry per account, epoch s, 0 unknown
        groups.append(group)
    return groups[:6]


class CpamcSource:
    """Background poller. `line()` returns the latest `proxy` serial message."""

    def __init__(self, base: str | None = None):
        self.base = base or load_base()
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

    def _credit_expiry(self, acc: dict, req: dict, url: str) -> int | None:
        """Soonest expiry (epoch s) of this account's available banked resets; None on failure.

        Read-only GET. Never call the sibling /consume endpoint: it spends a reset."""
        payload = {"auth_index": acc["auth_index"], "method": "GET", "url": url, "header": req["header"]}
        try:
            out = self._call("POST", "/v0/management/api-call", payload)
            if out.get("status_code") != 200:
                return None
            body = out.get("body")
            body = json.loads(body) if isinstance(body, str) else body
            times = [_epoch(c.get("expires_at")) for c in body.get("credits", [])
                     if isinstance(c, dict) and c.get("status") == "available"]
        except Exception as e:
            log.warn("cpamc.credit_expiry_error", err=type(e).__name__)
            return None
        times = [t for t in times if t > 0]
        return int(min(times)) if times else 0

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
                res = {"windows": wins, "probe_ok": True}
                credits = _get(body, prof.get("reset_credits"))
                if isinstance(credits, int):
                    res["rc"] = credits  # banked manual limit resets
                    if credits > 0 and prof.get("reset_credits_url"):
                        expiry = self._credit_expiry(acc, req, prof["reset_credits_url"])
                        if expiry is not None:
                            res["rx"] = expiry
                return res
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
        indices = {a.get("auth_index") for a in accounts if a.get("auth_index") and not a.get("disabled")}
        live = {idx: value for idx, value in self._live.items() if idx in indices}
        self._live_at = {idx: value for idx, value in self._live_at.items() if idx in indices}
        for a in accounts:
            prof = self.profiles.get(a.get("provider"))
            idx = a.get("auth_index")
            if a.get("disabled") or not prof or not idx:
                continue
            if now - self._live_at.get(idx, 0) >= LIVE_EVERY_S:
                res = self._live_one(a, prof)
                if res.get("windows") is None and not res.get("auth_failed") and idx in live:
                    res = {**live[idx], "probe_ok": False}  # retain quota, not proof of current health
                if res.get("rc", 0) > 0 and "rx" not in res and "rx" in live.get(idx, {}):
                    res["rx"] = live[idx]["rx"]  # expiry lookup failed this round; keep the last one
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
                return {"t": "proxy", "ts": int(now), "tz": time.localtime(now).tm_gmtoff or 0, "up": 0, "age": 0, "attn": 1, "g": []}
            groups = pool_groups(self._accounts, self._live, self.profiles, now)
            up = self._up
            age = int(now - self._ok_at) if self._ok_at else 0
        attn = (not up) or any(g["a"] for g in groups)
        result = {"t": "proxy", "ts": int(now), "tz": time.localtime(now).tm_gmtoff or 0,
                  "up": int(up), "age": age, "attn": int(attn), "g": groups}
        # Preserve valid JSON and aggregate data if an unusually large fleet exceeds
        # the firmware's line buffer. Missing q means aggregate-only legacy mode.
        if len(json.dumps(result, separators=(",", ":")).encode()) > 4095:
            for group in reversed(groups):
                for pool in group["p"]:
                    for win in pool["w"]:
                        win.pop("q", None)
                if len(json.dumps(result, separators=(",", ":")).encode()) <= 4095:
                    break
        return result
