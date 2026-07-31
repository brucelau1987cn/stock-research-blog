#!/usr/bin/env python3
"""Gate a US post-close cron by America/New_York wall clock.

Exit 0 only during the configured New York weekday/hour window.
Exit 1 otherwise. The default is 17:00 ET Monday-Friday.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", type=int, default=17)
    parser.add_argument("--minute-start", type=int, default=0)
    parser.add_argument("--minute-end", type=int, default=20)
    args = parser.parse_args()

    now = datetime.now(ZoneInfo("America/New_York"))
    valid = (
        now.weekday() < 5
        and now.hour == args.hour
        and args.minute_start <= now.minute <= args.minute_end
    )
    if valid:
        print(now.isoformat())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
