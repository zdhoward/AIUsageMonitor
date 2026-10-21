"""Pushes the device payload to the display over the USB-serial bridge (CH340 on this board).

One JSON object per line. Lines from the device starting with '@' are status messages
(boot/ack) and are logged; everything else is ignored. The port is opened with DTR/RTS
de-asserted so opening it does not reset the ESP32.
"""

from __future__ import annotations

import json
import threading
import time

from . import log

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # service still runs HTTP-only without pyserial
    serial = None
    list_ports = None

# USB-UART bridges used on ESP32 boards: WCH CH340/CH9102, Silicon Labs CP210x, FTDI.
KNOWN_BRIDGES = {(0x1A86, 0x7523), (0x1A86, 0x55D4), (0x10C4, 0xEA60), (0x0403, 0x6001)}


def find_port() -> str | None:
    if list_ports is None:
        return None
    for p in list_ports.comports():
        if (p.vid, p.pid) in KNOWN_BRIDGES:
            return p.device
    return None


class SerialLink:
    def __init__(self, port: str, baud: int, interval_s: float, get_payload):
        self.port_setting = port
        self.baud = baud
        self.interval_s = interval_s
        self.get_payload = get_payload
        self._stop = threading.Event()
        self._paused_until = 0.0
        self._ser = None
        self.device_hello: str | None = None
        self.last_ack: float | None = None
        self.last_push: float | None = None
        self.connected_port: str | None = None

    def pause(self, seconds: float) -> None:
        """Release the port (e.g. so a firmware upload can use it)."""
        self._paused_until = time.time() + seconds
        self._close("paused")

    def resume(self) -> None:
        self._paused_until = 0.0

    @property
    def paused(self) -> bool:
        return time.time() < self._paused_until

    def stop(self) -> None:
        self._stop.set()
        self._close("stopping")

    def _close(self, why: str) -> None:
        ser, self._ser = self._ser, None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
            log.event("serial.closed", port=self.connected_port, why=why)
        self.connected_port = None

    def _open(self) -> bool:
        if serial is None:
            return False
        port = find_port() if self.port_setting == "auto" else self.port_setting
        if not port:
            return False
        try:
            ser = serial.Serial()
            ser.port, ser.baudrate, ser.timeout, ser.write_timeout = port, self.baud, 0, 2
            ser.dtr = False
            ser.rts = False
            ser.open()
        except (serial.SerialException, OSError) as e:
            log.warn("serial.open_failed", port=port, err=str(e)[:120])
            return False
        self._ser, self.connected_port = ser, port
        log.event("serial.opened", port=port, baud=self.baud)
        return True

    def run(self) -> None:
        if serial is None:
            log.warn("serial.disabled", reason="pyserial not installed")
            return
        buf = b""
        next_push = 0.0
        retry_at = 0.0
        while not self._stop.is_set():
            now = time.time()
            if self.paused:
                self._stop.wait(0.5)
                continue
            if self._ser is None:
                if now < retry_at or not self._open():
                    retry_at = max(retry_at, now + 5)
                    self._stop.wait(1)
                    continue
                next_push = 0.0
            try:
                if now >= next_push:
                    line = json.dumps(self.get_payload(), separators=(",", ":")) + "\n"
                    self._ser.write(line.encode("utf-8"))
                    self.last_push = now
                    next_push = now + self.interval_s
                waiting = self._ser.in_waiting
                if waiting:
                    buf += self._ser.read(waiting)
                    *lines, buf = buf.split(b"\n")
                    for raw in lines:
                        self._on_device_line(raw.decode("utf-8", "replace").strip())
                    buf = buf[-2048:]
            except (serial.SerialException, OSError) as e:
                log.warn("serial.io_error", port=self.connected_port, err=str(e)[:120])
                self._close("error")
                retry_at = now + 3
                continue
            self._stop.wait(0.1)

    def _on_device_line(self, line: str) -> None:
        if not line.startswith("@"):
            return
        if line.startswith("@HELLO"):
            self.device_hello = line[1:]
            log.event("device.hello", info=line[7:])
        elif line.startswith("@ACK"):
            self.last_ack = time.time()
            log.debug("device.ack", info=line[5:])
        else:
            log.event("device.msg", info=line[1:120])
