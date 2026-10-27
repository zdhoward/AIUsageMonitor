"""Collects all sources into one State, and turns a State into the compact device payload."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import log
from .config import Settings
from .models import Account, Activity, UsageRecord
from .pricing import Pricing
from .sources import antigravity, opencode_db, openrouter, t3_activity, t3_limits
from .sources.session_logs import SessionLogScanner, codex_windows

PAYLOAD_VERSION = 1


@dataclass
class State:
    accounts: list[Account] = field(default_factory=list)
    activity: Activity = field(default_factory=lambda: Activity("unknown"))
    records: list[UsageRecord] = field(default_factory=list)
    free_records: list[UsageRecord] = field(default_factory=list)
    openrouter: openrouter.OpenRouterStatus | None = None
    errors: dict[str, str] = field(default_factory=dict)  # source -> short reason
    refreshed_at: float | None = None


# ---------------------------------------------------------------- collection


def discover_transcript_roots(t3_home: Path) -> list[tuple[str, str, Path]]:
    """(instance id, flavor, root) for each configured Claude/Codex account."""
    home = Path.home()
    try:
        settings = json.loads((t3_home / "userdata" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        settings = {}
    instances = dict(settings.get("providerInstances") or {})
    instances.setdefault("claudeAgent", {"driver": "claudeAgent"})
    instances.setdefault("codex", {"driver": "codex"})
    roots: dict[Path, tuple[str, str, Path]] = {}
    for iid, inst in instances.items():
        if not isinstance(inst, dict):
            continue
        driver = inst.get("driver")
        cfg = inst.get("config") or {}
        env = inst.get("environment") or {}
        if driver == "claudeAgent":
            base = cfg.get("homePath") or env.get("CLAUDE_CONFIG_DIR") or "~/.claude"
            root = Path(str(base).replace("~", str(home), 1)) / "projects"
            flavor = "claude"
        elif driver == "codex":
            base = cfg.get("homePath") or env.get("CODEX_HOME") or "~/.codex"
            root = Path(str(base).replace("~", str(home), 1)) / "sessions"
            flavor = "codex"
        else:
            continue
        # Accounts sharing a history directory count once (same rule as T3 Usage).
        roots.setdefault(root.resolve(), (iid, flavor, root))
    return list(roots.values())


def select_accounts(accounts: list[Account]) -> list[Account]:
    """Keep six at most without letting duplicate caches displace the pinned set.

    Order is otherwise untouched, so generic grids still show service order.
    Only when the model cap is exceeded are the requested providers (two
    Claude accounts, Codex, then Antigrav/Argon) ranked ahead of extras.
    """
    seen: dict[str, int] = {}
    unique: list[Account] = []
    for a in accounts:
        key = a.instance_id or f"{a.driver}:{a.name}"
        if key in seen:
            unique[seen[key]] = a  # a fresh reading replaces a retained copy
            continue
        seen[key] = len(unique)
        unique.append(a)
    if len(unique) <= 6:
        return unique

    # Only the first two Claude instances and the first Codex instance keep a
    # privileged rank. Duplicate Codex caches (or extra Claude logins) cannot
    # jump ahead of Antigrav/Argon and displace a requested provider.
    def priority(a: Account) -> int:
        if a.driver == "claudeAgent":
            return 0 if claude_seen[0] < 2 else 5
        if a.driver == "codex":
            return 1 if codex_seen[0] < 1 else 5
        if a.name == antigravity.ANTIGRAV_NAME:
            return 2
        if a.name == antigravity.ARGON_NAME:
            return 3
        return 5

    claude_seen, codex_seen = [0], [0]
    ranks = []
    for pos, a in enumerate(unique):
        rank = priority(a)
        ranks.append((rank, pos, a))
        if a.driver == "claudeAgent":
            claude_seen[0] += 1
        elif a.driver == "codex":
            codex_seen[0] += 1
    ranked = sorted(ranks, key=lambda item: (item[0], item[1]))
    keep = {id(item[2]) for item in ranked[:6]}
    return [a for a in unique if id(a) in keep]


class Collector:
    def __init__(self, settings: Settings):
        self.s = settings
        self.pricing = Pricing.load(settings.t3_home / "userdata" / "usage-model-rates.json")
        self.scanners = [
            SessionLogScanner(root, iid, flavor, settings.history_days)
            for iid, flavor, root in discover_transcript_roots(settings.t3_home)
        ]
        self.state = State()
        self._lock = threading.Lock()
        self._next_opencode = 0.0
        self._next_openrouter = 0.0
        self.antigravity = antigravity.AntigravityReader(
            settings.t3_home,
            refresh_s=settings.antigravity_refresh_s,
            timeout_s=settings.antigravity_timeout_s,
        )
        for sc in self.scanners:
            log.event("collector.transcripts", account=sc.account, flavor=sc.flavor, root=sc.root)

    def snapshot(self) -> State:
        with self._lock:
            return self.state

    def refresh(self, now: float | None = None) -> State:
        now = now or time.time()
        prev = self.state
        st = State(accounts=prev.accounts, records=prev.records,
                   openrouter=prev.openrouter, free_records=prev.free_records, refreshed_at=now)

        def guarded(name, fn):
            try:
                fn()
            except Exception as e:  # one broken source must not blank the others
                st.errors[name] = type(e).__name__
                log.warn("source.failed", src=name, err=type(e).__name__, detail=str(e)[:160])

        def limits():
            accounts = t3_limits.read_accounts(self.s.t3_home)
            if self.s.antigravity_enabled:
                # The cache's antigravity entry is the Claude & GPT shared 3p
                # allowance, not Gemini: suppress it rather than mislabel it.
                accounts = [a for a in accounts if a.driver != "antigravity"]
            st.accounts = select_accounts(accounts)

        def activity():
            st.activity = t3_activity.read_activity(
                self.s.t3_home / "userdata" / "statev2.sqlite", now, self.s.max_run_age_s
            )

        def transcripts():
            recs: list[UsageRecord] = []
            for sc in self.scanners:
                sc.refresh(now)
                recs.extend(sc.records().values())
            st.records = recs

        guarded("t3_limits", limits)
        if self.s.antigravity_enabled:
            def antigravity_direct():
                st.accounts = select_accounts(st.accounts + self.antigravity.read(now))

            guarded("antigravity", antigravity_direct)
        guarded("t3_activity", activity)
        guarded("transcripts", transcripts)
        if "t3_activity" in st.errors:
            st.activity = prev.activity
        self._merge_codex_log_limits(st)

        if now >= self._next_opencode:
            self._next_opencode = now + self.s.opencode_refresh_s

            def oc():
                st.free_records = opencode_db.read_records(self.s.opencode_db, now - self.s.history_days * 86400)

            guarded("opencode", oc)
        if self.s.openrouter_enabled and now >= self._next_openrouter:
            self._next_openrouter = now + self.s.openrouter_refresh_s
            st.openrouter = openrouter.fetch(now)
            if st.openrouter.error:
                log.warn("source.failed", src="openrouter", err=st.openrouter.error)

        with self._lock:
            self.state = st
        log.debug(
            "collector.refreshed",
            accounts=len(st.accounts),
            records=len(st.records),
            free=len(st.free_records),
            act=st.activity.state,
            errors=",".join(st.errors) or "-",
        )
        return st

    def _merge_codex_log_limits(self, st: State) -> None:
        """Codex logs carry rate limits on every token event; prefer them when newer."""
        for sc in self.scanners:
            if sc.flavor != "codex":
                continue
            latest = sc.latest_rate_limits()
            if not latest:
                continue
            ts, payload = latest
            for acct in st.accounts:
                if acct.instance_id == sc.account and (acct.checked_at or 0) < ts:
                    windows = codex_windows(payload)
                    if windows:
                        acct.windows, acct.checked_at, acct.source, acct.unavailable = windows, ts, "codex_log", None


# ---------------------------------------------------------------- device payload


def short_model(model: str | None) -> str:
    if not model:
        return ""
    m = model.split("/")[-1]
    if m.startswith("claude-"):
        m = m[len("claude-"):]
    for suffix in (":free", "-free"):
        if m.endswith(suffix):
            m = m[: -len(suffix)]
    return m[:22]


def local_midnight(now: float) -> float:
    d = datetime.fromtimestamp(now)
    return d.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def _cents(usd: float) -> int:
    return int(round(usd * 100))


def build_payload(st: State, now: float, pricing: Pricing, settings: Settings, seq: int = 0) -> dict:
    names = {a.instance_id: a.name for a in st.accounts}
    day0 = local_midnight(now)
    hour0 = now - (now % 3600)
    payload: dict = {
        "v": PAYLOAD_VERSION,
        "seq": seq,
        "hm": datetime.fromtimestamp(now).strftime("%H:%M"),
        "ok": 0 if st.errors else 1,
    }
    if st.errors:
        payload["err"] = ",".join(sorted(st.errors))[:40]

    # Activity
    a = st.activity
    if a.state == "unknown":
        payload["act"] = {"s": "na"}
    else:
        act = {"s": "run" if a.state == "running" else "idle"}
        if a.instance_id:
            act["p"] = names.get(a.instance_id, a.instance_id)[:10]
        if a.model:
            act["m"] = short_model(a.model)
        if a.running > 1:
            act["n"] = a.running
        if a.since:
            act["t"] = max(int(now - a.since), 0)
        payload["act"] = act

    # Quota windows
    accs = []
    best = None  # (used, account, label)
    for acct in st.accounts:
        age = int(now - acct.checked_at) if acct.checked_at else -1
        stale = age < 0 or age > settings.limits_stale_s
        entry = {"p": acct.name[:8], "c": acct.color or "888888", "age": age, "st": 1 if stale else 0}
        if acct.plan:
            entry["pl"] = acct.plan
        if acct.unavailable:
            entry["x"] = acct.unavailable[:20]
        if acct.reset_credits is not None and acct.reset_credits >= 0:
            entry["rc"] = acct.reset_credits
        ws = []
        for w in acct.windows[:3]:
            used = -1 if w.used_percent is None else int(round(w.used_percent))
            if w.resets_at is None:
                remain = -1
            elif w.resets_at <= now:
                remain = 0  # retain the last measured usage until a new reading arrives
            else:
                remain = int(w.resets_at - now)
            ws.append({"l": w.label, "u": used, "r": remain})
            if used >= 0 and not stale and (best is None or used > best[0]):
                best = (used, acct.name, w.label)
        entry["w"] = ws
        accs.append(entry)
    payload["acc"] = accs
    if best:
        payload["hi"] = {"u": best[0], "p": best[1][:8], "w": best[2]}

    # Subscription-account token usage and API-equivalent estimate
    hourly = [0.0] * 24
    by_acct: dict[str, float] = {}
    c1 = c7 = 0.0
    i1 = cr1 = o1 = unpriced = 0
    for r in st.records:
        cost = pricing.cost(r.model, r.uncached_in, r.cache_read, r.cache_write, r.out)
        if r.ts >= now - 7 * 86400:
            c7 += cost or 0.0
        if r.ts >= day0:
            c1 += cost or 0.0
            i1 += r.uncached_in + r.cache_write
            cr1 += r.cache_read
            o1 += r.out
            by_acct[r.account] = by_acct.get(r.account, 0.0) + (cost or 0.0)
            if cost is None:
                unpriced += r.uncached_in + r.out
        idx = 23 - int((hour0 - (r.ts - r.ts % 3600)) // 3600)
        if 0 <= idx < 24:
            hourly[idx] += cost or 0.0
    payload["use"] = {
        "c1": _cents(c1),
        "c7": _cents(c7),
        "i1": i1,
        "cr1": cr1,
        "o1": o1,
        "unp": 1 if unpriced else 0,
        "h": [_cents(x) for x in hourly],
    }
    payload["byp"] = [
        {"p": names.get(k, k)[:8], "c1": _cents(v)} for k, v in sorted(by_acct.items(), key=lambda kv: -kv[1])
    ][:4]

    # Free / other providers (OpenCode history), today
    free_today = [r for r in st.free_records if r.ts >= day0 and opencode_db.is_free(r, settings.extra_free_providers)]
    models: dict[str, int] = {}
    for r in free_today:
        models[r.model] = models.get(r.model, 0) + 1
    free = {"n": len(free_today), "t": sum(r.uncached_in + r.cache_read + r.out for r in free_today)}
    if models:
        free["m"] = short_model(max(models.items(), key=lambda kv: kv[1])[0])
    payload["free"] = free
    payload["nim"] = {"n": sum(1 for r in free_today if r.account == "opencode:nvidia")}

    # OpenRouter key status
    o = st.openrouter
    if o is None:
        payload["or"] = {"x": "pending"}
    elif o.error:
        payload["or"] = {"x": o.error[:16], "age": int(now - o.checked_at)}
    else:
        ent = {"age": int(now - o.checked_at)}
        if o.free_used is not None and o.free_limit is not None:
            ent["fu"], ent["fl"] = o.free_used, o.free_limit
        if o.usd_daily is not None:
            ent["d"] = _cents(o.usd_daily)
        if o.budget_remaining is not None:
            ent["b"] = _cents(o.budget_remaining)
        payload["or"] = ent
    return payload


def build_status(st: State, now: float) -> dict:
    """Richer JSON for humans/debugging at /v1/status. Never includes e-mails or tokens."""
    return {
        "refreshed_at": st.refreshed_at,
        "errors": st.errors,
        "activity": st.activity.__dict__,
        "accounts": [
            {
                "instance": a.instance_id,
                "name": a.name,
                "plan": a.plan,
                "source": a.source,
                "checked_at": a.checked_at,
                "unavailable": a.unavailable,
                "reset_credits": a.reset_credits,
                "windows": [w.__dict__ for w in a.windows],
            }
            for a in st.accounts
        ],
        "records": len(st.records),
        "free_records": len(st.free_records),
        "openrouter": st.openrouter.__dict__ if st.openrouter else None,
    }
