"""
Purpose: query ThreatVectr public monthly ransomware reports for aggregate trend and ranking sanity checks.
When used: for monthly/period statistics, rankings, and mandatory all-source aggregate corroboration.
Why it exists: ThreatVectr provides current aggregate reports but should not be used as a victim-level replacement when victim records are not exposed.
Inputs/parameters: CLI operation plus validated year and month.
Outputs: exactly one JSON object on stdout with bounded parsed HTML content and aggregate-only provenance.
High-level behavior: constructs the documented monthly report path from an English month slug and retrieves it over HTTPS.
Failure semantics: successful retrieval qualifies only for aggregate/statistical use and never as proof of a victim-level record.
"""
from __future__ import annotations

import argparse
import calendar

from _cli_common import bounded_int, print_json
from _source_runner import execute

BASE_URL = "https://threatvectr.com"
SOURCE = "threatvectr"


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    if args.operation != "month":
        raise ValueError("unsupported operation")
    year = bounded_int(str(args.year), 2000, 2100)
    month = bounded_int(str(args.month), 1, 12)
    slug = calendar.month_name[month].casefold()
    return f"/ransomware-tracker/reports/{slug}-{year}", None, {
        "operation": "month",
        "year": year,
        "month": month,
        "data_type": "aggregate-statistics",
        "victim_level": False,
        "lineage": "reported-as-ransomware.live-observed-claims",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="threatvectr.py")
    sub = parser.add_subparsers(dest="operation", required=True)
    month = sub.add_parser("month")
    month.add_argument("year", type=lambda value: bounded_int(value, 2000, 2100))
    month.add_argument("month", type=lambda value: bounded_int(value, 1, 12))
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
            "error": {"type": "invalid_input", "message": str(exc), "status": None},
        })
        return 2
    return execute(SOURCE, BASE_URL, path, query, meta, profile="html")


if __name__ == "__main__":
    raise SystemExit(main())
