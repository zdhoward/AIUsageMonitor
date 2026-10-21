"""Run: python -m aimon [--once] [--no-serial] [--port COM6] [-v]"""

from __future__ import annotations

import argparse
import json
import sys
import time

from . import log
from .config import Settings
from .snapshot import Collector, build_payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aimon", description="Local AI usage monitor service for the ESP32 display.")
    ap.add_argument("--once", action="store_true", help="collect once, print the device payload, exit")
    ap.add_argument("--no-serial", action="store_true", help="don't push to the display over USB serial")
    ap.add_argument("--port", help="serial port (default: auto-detect)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    s = Settings.load()
    if args.no_serial:
        s.serial_enabled = False
    if args.port:
        s.serial_port = args.port
    log.setup(s.log_dir, args.verbose)

    if args.once:
        c = Collector(s)
        st = c.refresh()
        print(json.dumps(build_payload(st, time.time(), c.pricing, s), indent=1))
        return 0

    from .server import App

    try:
        App(s).serve()
    except KeyboardInterrupt:
        pass
    except OSError as e:
        log.warn("service.bind_failed", err=str(e)[:160])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
