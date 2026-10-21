"""Grep-friendly key=value logging: `ts=... lvl=INFO evt=source.ok src=t3_limits n=3`."""

from __future__ import annotations

import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

_log = logging.getLogger("aimon")


def setup(log_dir: Path, verbose: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(message)s")
    file_handler = RotatingFileHandler(log_dir / "aimon.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    _log.handlers[:] = [file_handler]
    if sys.stderr is not None:  # None under pythonw (background service)
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(fmt)
        _log.handlers.append(stream)
    _log.setLevel(logging.DEBUG if verbose else logging.INFO)


def _fmt(v) -> str:
    s = str(v)
    if not s or any(c in s for c in ' "='):
        s = '"' + s.replace('"', "'") + '"'
    return s


def event(evt: str, lvl: int = logging.INFO, **kv) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    parts = [f"ts={ts}", f"lvl={logging.getLevelName(lvl)}", f"evt={evt}"]
    parts += [f"{k}={_fmt(v)}" for k, v in kv.items()]
    _log.log(lvl, " ".join(parts))


def warn(evt: str, **kv) -> None:
    event(evt, logging.WARNING, **kv)


def debug(evt: str, **kv) -> None:
    event(evt, logging.DEBUG, **kv)
