"""Provider-neutral data shapes passed from adapters to the snapshot builder."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Window:
    id: str  # provider window id, e.g. five_hour / seven_day / primary
    kind: str  # session | weekly | other
    label: str  # short label for the screen: 5h, 7d, ...
    used_percent: float | None  # None = not reported
    resets_at: float | None  # epoch seconds
    window_mins: int | None = None


@dataclass
class Account:
    """One subscription account (provider instance) with its quota windows."""

    instance_id: str
    name: str  # display name, never the e-mail
    driver: str  # claudeAgent | codex | ...
    plan: str | None
    color: str | None  # hex without '#'
    windows: list[Window] = field(default_factory=list)
    checked_at: float | None = None
    source: str = "t3_cache"
    unavailable: str | None = None  # reason when no limits are reported
    reset_credits: int | None = None  # banked limit resets, when the provider reports them


@dataclass
class UsageRecord:
    """One completed model call, as recorded in local history."""

    ts: float
    account: str  # provider instance id or opencode provider id
    model: str
    uncached_in: int
    cache_read: int
    cache_write: int
    out: int
    reported_cost: float | None = None  # provider-reported USD (OpenCode), else None


@dataclass
class Activity:
    state: str  # running | idle | unknown
    instance_id: str | None = None
    model: str | None = None
    running: int = 0
    since: float | None = None  # run start (running) or last completion (idle)
