"""
Purpose: query the public DDoSia Monitor CTI API for NoName057/DDoSia target intelligence.
When used: for DDoS target lookups, recent DDoSia target checks, date-based extraction, available-date discovery, and DDoSia trend/statistics requests.
Why it exists: adds DDoS target intelligence beside the ransomware trackers without conflating DDoS target observations with ransomware victim records.
Inputs/parameters: CLI operation plus validated host, date, limit, or statistics type.
Outputs: exactly one JSON object on stdout using the shared source envelope.
High-level behavior: constructs documented DDoSia Monitor API requests and delegates HTTPS execution to the shared source runner.
Failure semantics: invalid input fails locally; HTTP/network errors remain explicit source states and never imply that a host was not targeted.
"""
from __future__ import annotations

import argparse
import re
from typing import Any

from _cli_common import bounded_int, print_json, query_text
from _source_runner import execute

BASE_URL = "https://ddosia.rfeed.it"
SOURCE = "DDoSia Monitor"

STAT_TYPES = {
    "overview",
    "by_year",
    "by_month",
    "by_day",
    "timeseries_monthly",
    "timeseries_daily",
}


def _date(value: str) -> str:
    cleaned = query_text(value, "date", 10)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        raise ValueError("date must be YYYY-MM-DD")
    return cleaned


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, Any] | None, dict[str, Any]]:
    op = args.operation

    if op == "recent":
        limit = bounded_int(str(args.limit), 1, 500)
        return "/api/recent_targets.php", {"limit": limit}, {
            "operation": op,
            "limit": limit,
            "channel": "API",
            "data_type": "ddosia-target-observation",
        }

    if op == "search":
        host = query_text(args.host, "host", 253)
        return "/api/search_host.php", {"host": host}, {
            "operation": op,
            "host": host,
            "channel": "API",
            "data_type": "ddosia-target-observation",
        }

    if op == "date":
        date = _date(args.date)
        return "/api/targets_by_date.php", {"date": date}, {
            "operation": op,
            "date": date,
            "channel": "API",
            "data_type": "ddosia-target-observation",
        }

    if op == "dates":
        return "/api/available_dates.php", None, {
            "operation": op,
            "channel": "API",
            "data_type": "ddosia-coverage-calendar",
        }

    if op == "stats":
        stat_type = query_text(args.stat_type, "stat_type", 40)
        if stat_type not in STAT_TYPES:
            raise ValueError("unsupported statistics type")
        return "/api/stats.php", {"type": stat_type}, {
            "operation": op,
            "stat_type": stat_type,
            "channel": "API",
            "data_type": "ddosia-aggregate-statistics",
        }

    raise ValueError("unsupported operation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ddosia.py")
    sub = parser.add_subparsers(dest="operation", required=True)

    recent = sub.add_parser("recent")
    recent.add_argument("--limit", type=lambda x: bounded_int(x, 1, 500), default=20)

    search = sub.add_parser("search")
    search.add_argument("host")

    date = sub.add_parser("date")
    date.add_argument("date")

    sub.add_parser("dates")

    stats = sub.add_parser("stats")
    stats.add_argument("stat_type", choices=sorted(STAT_TYPES))

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        path, query, meta = build_request(args)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        print_json({
            "ok": False,
            "state": "INVALID_RESPONSE",
            "source": SOURCE,
            "request": {"operation": getattr(args, "operation", None)},
            "status": None,
            "data": None,
            "error": {
                "type": "invalid_input",
                "message": str(exc),
                "status": None,
            },
        })
        return 2

    return execute(SOURCE, BASE_URL, path, query, meta, profile="api")


if __name__ == "__main__":
    raise SystemExit(main())
