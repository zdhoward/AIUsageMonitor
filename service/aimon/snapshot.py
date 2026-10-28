"""Collects all sources into one State, and turns a State into the compact device payload."""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from . import log
from .config import Settings
from .models import Account, Activity, UsageRecord
from .pricing import Pricing
from .quota_history import QuotaHistory
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


def _cadence(value, default: float) -> float:
    """Configured interval clamped to a usable positive value."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    if value != value:  # NaN
        return default
    return max(value, 1.0)


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
            SessionLogScanner(root, iid, flavor, settings.history_days, settings.transcript_discovery_s)
            for iid, flavor, root in discover_transcript_roots(settings.t3_home)
        ]
        self.state = State()
        self._lock = threading.Lock()
        self._next_opencode = 0.0
        self._next_openrouter = 0.0
        self.quota = QuotaHistory(settings.log_dir / "quota_history.jsonl", settings.quota_history_entries)
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

    def refresh(self, now: float | None = None, heavy: bool = True) -> State:
        """Refresh sources and publish a new State.

        ``heavy=False`` is the lightweight pass: it rereads the local quota
        caches, activity and the already-parsed Codex rate limits, while every
        heavy metric (transcripts, OpenCode history, OpenRouter status) is
        carried over from the previous snapshot. A fast lightweight cadence
        therefore never recomputes transcript aggregates.
        """
        now = now or time.time()
        prev = self.state
        st = State(accounts=list(prev.accounts), records=prev.records,
                   activity=prev.activity, openrouter=prev.openrouter,
                   free_records=prev.free_records, errors=dict(prev.errors), refreshed_at=now)

        def guarded(name, fn):
            try:
                fn()
            except Exception as e:  # one broken source must not blank the others
                st.errors[name] = type(e).__name__
                log.warn("source.failed", src=name, err=type(e).__name__, detail=str(e)[:160])
            else:
                st.errors.pop(name, None)

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
            # Reuse the previous list when nothing changed, so the payload
            # aggregate cache survives an unchanged heavy pass too.
            if len(recs) == len(prev.records) and all(a is b for a, b in zip(recs, prev.records)):
                return
            st.records = recs

        guarded("t3_limits", limits)
        if self.s.antigravity_enabled:
            def antigravity_direct():
                st.accounts = select_accounts(st.accounts + self.antigravity.read(now))

            guarded("antigravity", antigravity_direct)
        guarded("t3_activity", activity)
        if heavy:
            guarded("transcripts", transcripts)
        self._merge_codex_log_limits(st)

        if heavy:
            if now >= self._next_opencode:
                self._next_opencode = now + _cadence(self.s.opencode_refresh_s, 30.0)

                def oc():
                    st.free_records = opencode_db.read_records(self.s.opencode_db, now - self.s.history_days * 86400)

                guarded("opencode", oc)
            if self.s.openrouter_enabled and now >= self._next_openrouter:
                self._next_openrouter = now + _cadence(self.s.openrouter_refresh_s, 600.0)
                st.openrouter = openrouter.fetch(now)
                if st.openrouter.error:
                    log.warn("source.failed", src="openrouter", err=st.openrouter.error)

        # Local transition history: bounded, best-effort, never fatal.
        self.quota.observe(st.accounts, now)

        with self._lock:
            self.state = st
        log.debug(
            "collector.refreshed",
            heavy=int(heavy),
            accounts=len(st.accounts),
            records=len(st.records),
            free=len(st.free_records),
            act=st.activity.state,
            errors=",".join(st.errors) or "-",
        )
        return st

    def _merge_codex_log_limits(self, st: State) -> None:
        """Codex logs carry rate limits on every token event; prefer them when newer.

        A published Account object is never mutated: the newer reading replaces
        the entry with a fresh copy so an earlier snapshot keeps its values.
        """
        for sc in self.scanners:
            if sc.flavor != "codex":
                continue
            latest = sc.latest_rate_limits()
            if not latest:
                continue
            ts, payload = latest
            for pos, acct in enumerate(st.accounts):
                if acct.instance_id == sc.account and (acct.checked_at or 0) < ts:
                    windows = codex_windows(payload)
                    if windows:
                        st.accounts[pos] = replace(
                            acct, windows=windows, checked_at=ts, source="codex_log", unavailable=None
                        )


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


def _used_percent(window) -> int:
    """Rounded used percentage that never hides known fractional availability."""
    if window.used_percent is None or not math.isfinite(window.used_percent):
        return -1
    value = int(round(window.used_percent))
    if window.used_percent < 100 and value >= 100:
        return 99  # 99.6% used still has quota left; 100 means exhausted
    return value


class _UsageCache:
    """Last usage aggregate, keyed by snapshot identity and hour/day bounds.

    The records lists are held so their ids cannot be reused by another object
    while the cached aggregate is still valid.
    """

    def __init__(self):
        self.key = None
        self.value: dict | None = None
        self.held: tuple = ()

    def get(self, st: State, now: float, pricing: Pricing, settings: Settings,
            day0: float, hour0: float) -> dict:
        key = (
            id(st.records), id(st.free_records), id(pricing),
            day0, hour0, tuple(settings.extra_free_providers),
        )
        if key == self.key and len(self.held) == 2 and self.held[0] is st.records and self.held[1] is st.free_records:
            return self.value
        value = _aggregate_usage(st, now, pricing, settings, day0, hour0)
        self.key, self.value, self.held = key, value, (st.records, st.free_records)
        return value


_USAGE_CACHE = _UsageCache()
_USAGE_LOCK = threading.Lock()


def _aggregate_usage(st: State, now: float, pricing: Pricing, settings: Settings,
                     day0: float, hour0: float) -> dict:
    """Cost/token/free-provider aggregates for one immutable snapshot."""
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

    free_today = [r for r in st.free_records if r.ts >= day0 and opencode_db.is_free(r, settings.extra_free_providers)]
    models: dict[str, int] = {}
    for r in free_today:
        models[r.model] = models.get(r.model, 0) + 1
    free = {"n": len(free_today), "t": sum(r.uncached_in + r.cache_read + r.out for r in free_today)}
    if models:
        free["m"] = short_model(max(models.items(), key=lambda kv: kv[1])[0])

    return {
        "use": {
            "c1": _cents(c1),
            "c7": _cents(c7),
            "i1": i1,
            "cr1": cr1,
            "o1": o1,
            "unp": 1 if unpriced else 0,
            "h": [_cents(x) for x in hourly],
        },
        "byp": [
            {"p": r, "c1": _cents(v)} for r, v in sorted(by_acct.items(), key=lambda kv: -kv[1])
        ][:4],
        "free": free,
        "nim": {"n": sum(1 for r in free_today if r.account == "opencode:nvidia")},
    }


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
    # How long before a reset available quota should keep the dashboards awake.
    # The actual reset countdown is unchanged; absent/negative means due-only.
    warning = getattr(settings, "reset_warning_s", 0)
    try:
        payload["warn"] = min(max(int(warning), 0), 2147483647)
    except (TypeError, ValueError, OverflowError):
        payload["warn"] = 0

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
            used = _used_percent(w)
            if w.resets_at is None or not math.isfinite(w.resets_at):
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

    # Subscription-account token usage and API-equivalent estimate. The heavy
    # aggregate is cached: heartbeats and countdown-only payloads reuse it.
    with _USAGE_LOCK:
        agg = _USAGE_CACHE.get(st, now, pricing, settings, day0, hour0)
    payload["use"] = agg["use"]
    payload["byp"] = [{"p": names.get(e["p"], e["p"])[:8], "c1": e["c1"]} for e in agg["byp"]]
    payload["free"] = dict(agg["free"])
    payload["nim"] = agg["nim"]

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
