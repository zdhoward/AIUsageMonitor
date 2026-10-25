"""PC resource snapshot for the display's System page (Task Manager style).

`sample()` returns a compact dict sent as its own `{"t":"sys",...}` serial line
about once a second, separate from the usage payload so the 4 KB usage push stays
at its own cadence. Rates are computed from the previous call. Sampling must stay
cheap (a few ms): it runs on the serial thread. Without psutil the page shows
"unavailable"; GPU load is Windows-only and omitted elsewhere.
"""

from __future__ import annotations

import sys
import time

try:
    import psutil
except ImportError:
    psutil = None


class GpuLoad:
    """GPU load as Task Manager reports it: the busiest engine type's summed
    utilization, read from the "GPU Engine" performance counters through PDH."""

    def __init__(self) -> None:
        self._counter = None
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes as W

            class Value(ctypes.Structure):
                _fields_ = [("status", W.DWORD), ("pad", W.DWORD), ("value", ctypes.c_double)]

            class Item(ctypes.Structure):
                _fields_ = [("name", W.LPWSTR), ("v", Value)]

            self._ct, self._W, self._Item = ctypes, W, Item
            self._pdh = ctypes.windll.pdh
            self._query, counter = W.HANDLE(), W.HANDLE()
            if self._pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._query)):
                return
            path = "\\GPU Engine(*)\\Utilization Percentage"
            if self._pdh.PdhAddEnglishCounterW(self._query, path, 0, ctypes.byref(counter)):
                return
            self._pdh.PdhCollectQueryData(self._query)  # rates need two samples
            self._counter = counter
        except Exception:
            self._counter = None

    def read(self) -> int | None:
        if self._counter is None:
            return None
        ct, W = self._ct, self._W
        try:
            self._pdh.PdhCollectQueryData(self._query)
            size, n = W.DWORD(0), W.DWORD(0)
            # PDH_FMT_DOUBLE | PDH_FMT_NOCAP100; the first call sizes the buffer.
            self._pdh.PdhGetFormattedCounterArrayW(self._counter, 0x8200, ct.byref(size), ct.byref(n), None)
            if not size.value:
                return 0
            buf = ct.create_string_buffer(size.value)
            if self._pdh.PdhGetFormattedCounterArrayW(self._counter, 0x8200, ct.byref(size), ct.byref(n), buf):
                return None
            items = ct.cast(buf, ct.POINTER(self._Item))
            engines: dict[str, float] = {}
            for i in range(n.value):
                kind = items[i].name.rsplit("engtype_", 1)[-1]
                engines[kind] = engines.get(kind, 0.0) + items[i].v.value
            return min(100, round(max(engines.values(), default=0.0)))
        except Exception:
            return None


class SysSampler:
    def __init__(self) -> None:
        self._last: tuple[float, int, int, int, int] | None = None
        self._gpu = GpuLoad() if psutil else None
        if psutil:
            psutil.cpu_percent()  # prime the first interval

    def sample(self) -> dict | None:
        if psutil is None:
            return None
        now = time.time()
        vm = psutil.virtual_memory()
        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()
        cur = (now, disk.read_bytes if disk else 0, disk.write_bytes if disk else 0, net.bytes_recv, net.bytes_sent)
        rates = [0, 0, 0, 0]
        if self._last and now > self._last[0]:
            dt = now - self._last[0]
            rates = [max(0, int((cur[i] - self._last[i]) / dt / 1024)) for i in range(1, 5)]
        self._last = cur
        out = {
            "t": "sys",
            "c": round(psutil.cpu_percent()),
            "mu": vm.used // 1048576,
            "mt": vm.total // 1048576,
            "dr": rates[0], "dw": rates[1],  # KiB/s
            "nr": rates[2], "ns": rates[3],
        }
        gpu = self._gpu.read() if self._gpu else None
        if gpu is not None:
            out["g"] = gpu
        return out
