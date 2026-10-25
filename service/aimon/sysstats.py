"""PC resource snapshot for the display's System page (Task Manager style).

`sample()` returns a compact dict sent as its own `{"t":"sys",...}` serial line
about once a second, separate from the usage payload so the 4 KB usage push stays
at its own cadence. Rates are computed from the previous call. Without psutil
the page shows "unavailable".
"""

from __future__ import annotations

import time

try:
    import psutil
except ImportError:
    psutil = None

MAX_CORES = 16


class SysSampler:
    def __init__(self) -> None:
        self._last: tuple[float, int, int, int, int] | None = None
        self._procs: dict[int, "psutil.Process"] = {}
        self._procs_at = 0.0
        self._top: list[list] = []
        if psutil:
            psutil.cpu_percent(percpu=True)  # prime the first interval

    def sample(self) -> dict | None:
        if psutil is None:
            return None
        now = time.time()
        cores = psutil.cpu_percent(percpu=True)
        vm = psutil.virtual_memory()
        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()
        cur = (now, disk.read_bytes if disk else 0, disk.write_bytes if disk else 0, net.bytes_recv, net.bytes_sent)
        rates = [0, 0, 0, 0]
        if self._last and now > self._last[0]:
            dt = now - self._last[0]
            rates = [max(0, int((cur[i] - self._last[i]) / dt / 1024)) for i in range(1, 5)]
        self._last = cur
        if now - self._procs_at >= 3:  # process scan is the expensive part
            self._procs_at = now
            self._top = self._top_processes()
        out = {
            "t": "sys",
            "c": round(sum(cores) / len(cores)) if cores else 0,
            "k": [round(c) for c in cores[:MAX_CORES]],
            "mu": vm.used // 1048576,
            "mt": vm.total // 1048576,
            "dr": rates[0], "dw": rates[1],  # KiB/s
            "nr": rates[2], "ns": rates[3],
            "p": self._top,
        }
        try:
            out["up"] = int(now - psutil.boot_time())
        except Exception:
            pass
        return out

    def _top_processes(self) -> list[list]:
        """Top three processes by CPU share of the whole machine, as [name, percent]."""
        seen: dict[int, "psutil.Process"] = {}
        rows = []
        ncpu = psutil.cpu_count() or 1
        for p in psutil.process_iter(["name"]):
            proc = self._procs.get(p.pid, p)
            seen[p.pid] = proc
            try:
                pct = proc.cpu_percent(None) / ncpu
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            name = (p.info.get("name") or "?").removesuffix(".exe")
            if p.pid and name != "System Idle Process":
                rows.append((pct, name[:14]))
        self._procs = seen
        rows.sort(reverse=True)
        return [[n, round(c)] for c, n in rows[:3]]
