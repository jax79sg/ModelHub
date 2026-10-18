"""The error-rate measure of the services: the share of 5xx access lines (catalog NFR6.3).

    python3 error_rate.py <log file> [--fail-above 0.05]

Reads the JSON log lines of the services (a `docker compose logs` file works: the container
prefix before "|" is ignored), counts the lines with event "access" per service and how many of
them have a status of 500 or more, and prints one line per service. With --fail-above the exit
status is 1 when any service is over that share, so a scheduled job can alert on it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable


def error_rates(lines: Iterable[str]) -> dict[str, dict]:
    totals: dict[str, dict] = {}
    for raw in lines:
        text = raw.split("| ", 1)[1] if "| " in raw and not raw.lstrip().startswith("{") else raw
        try:
            entry = json.loads(text)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("event") != "access":
            continue
        status = entry.get("status")
        if not isinstance(status, int):
            continue
        row = totals.setdefault(str(entry.get("service", "unknown")), {"requests": 0, "errors": 0})
        row["requests"] += 1
        row["errors"] += status >= 500
    for row in totals.values():
        row["share"] = row["errors"] / row["requests"]
    return totals


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("logfile")
    parser.add_argument("--fail-above", type=float, default=None)
    args = parser.parse_args(argv)
    with open(args.logfile, encoding="utf-8", errors="replace") as handle:
        rates = error_rates(handle)
    worst = 0.0
    for service, row in sorted(rates.items()):
        print(
            f"{service}: {row['errors']} of {row['requests']} requests failed ({row['share']:.1%})"
        )
        worst = max(worst, row["share"])
    if not rates:
        print("No access lines found.")
    return 1 if args.fail_above is not None and worst > args.fail_above else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
