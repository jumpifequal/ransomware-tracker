"""
Purpose: query the current ransomware.live free v2 endpoints and provide client-side victim search.
When used: for recent victims, month-specific victims, groups, group victims, country victims, sector victims, and recent keyword search.
Why it exists: replaces obsolete search endpoint assumptions with stable documented v2 endpoints while preserving portable JSON output.
Inputs/parameters: CLI operation plus validated group/country/sector/year/month/query values.
Outputs: exactly one JSON object on stdout with normalized source state and data.
High-level behavior: maps CLI operations to current v2 paths; the `search` operation fetches recent victims and filters locally by case-insensitive substring.
Failure semantics: invalid local input fails before network access; remote failures return machine-readable JSON with explicit source state.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from _cli_common import bounded_int, path_segment, print_json, query_text, source_state
from _http_common import SafeRequestError, get
from _source_runner import execute

BASE_URL = "https://api.ransomware.live/v2"
SOURCE = "ransomware.live"


def _records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("victims", "results", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []



def _is_semantic_empty_404(operation: str, exc: SafeRequestError) -> bool:
    if operation != "month" or exc.status != 404:
        return False
    body = (exc.body or "").casefold()
    return "no victims found" in body


def run_month(path: str, request_meta: dict[str, object]) -> int:
    try:
        response = get(BASE_URL, path)
        data = response["data"]
        print_json(
            {
                "ok": True,
                "state": source_state(True, response["status"], data),
                "source": SOURCE,
                "request": request_meta,
                "status": response["status"],
                "data": data,
                "error": None,
            }
        )
        return 0
    except SafeRequestError as exc:
        if _is_semantic_empty_404("month", exc):
            print_json(
                {
                    "ok": True,
                    "state": "EMPTY",
                    "source": SOURCE,
                    "request": request_meta,
                    "status": exc.status,
                    "data": {
                        "results": [],
                        "upstream_message": (exc.body or "").strip()[:1000],
                    },
                    "error": None,
                }
            )
            return 0

        print_json(
            {
                "ok": False,
                "state": source_state(False, exc.status, None),
                "source": SOURCE,
                "request": request_meta,
                "status": exc.status,
                "data": None,
                "error": {
                    "type": exc.kind,
                    "message": exc.message,
                    "status": exc.status,
                },
            }
        )
        return 2

def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    operation = args.operation
    if operation == "recent":
        return "/recentvictims", None, {"operation": operation}
    if operation == "groups":
        return "/groups", None, {"operation": operation}
    if operation == "group":
        group = path_segment(args.group_name, "group_name")
        return f"/group/{group}", None, {
            "operation": operation,
            "group_name": args.group_name,
        }
    if operation == "group-victims":
        group = path_segment(args.group_name, "group_name")
        return f"/groupvictims/{group}", None, {
            "operation": operation,
            "group_name": args.group_name,
        }
    if operation == "month":
        year = args.year
        month = args.month
        return f"/victims/{year}/{month:02d}", None, {
            "operation": operation,
            "year": year,
            "month": month,
        }
    if operation == "country":
        country = path_segment(args.country_code.upper(), "country_code", 3)
        return f"/countryvictims/{country}", None, {
            "operation": operation,
            "country_code": args.country_code.upper(),
        }
    if operation == "sector":
        sector = path_segment(args.sector, "sector")
        return f"/sectorvictims/{sector}", None, {
            "operation": operation,
            "sector": args.sector,
        }
    raise ValueError("unsupported operation")


def run_search(keyword: str) -> int:
    cleaned = query_text(keyword, "keyword")
    request_meta = {"operation": "search", "keyword": cleaned}
    try:
        response = get(BASE_URL, "/recentvictims")
        records = _records(response["data"])
        needle = cleaned.casefold()
        matches = []
        for item in records:
            fields = (
                str(item.get("victim") or ""),
                str(item.get("website") or item.get("domain") or ""),
                str(item.get("description") or ""),
            )
            if any(needle in value.casefold() for value in fields if value):
                matches.append(item)

        data = {
            "scope": "recentvictims",
            "query": cleaned,
            "count": len(matches),
            "results": matches,
        }
        print_json(
            {
                "ok": True,
                "state": "OK" if matches else "EMPTY",
                "source": SOURCE,
                "request": request_meta,
                "status": response["status"],
                "data": data,
                "error": None,
            }
        )
        return 0
    except SafeRequestError as exc:
        print_json(
            {
                "ok": False,
                "state": source_state(False, exc.status, None),
                "source": SOURCE,
                "request": request_meta,
                "status": exc.status,
                "data": None,
                "error": {
                    "type": exc.kind,
                    "message": exc.message,
                    "status": exc.status,
                },
            }
        )
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ransomware_live.py")
    sub = parser.add_subparsers(dest="operation", required=True)

    sub.add_parser("recent")
    sub.add_parser("groups")

    group = sub.add_parser("group")
    group.add_argument("group_name")

    group_victims = sub.add_parser("group-victims")
    group_victims.add_argument("group_name")

    month = sub.add_parser("month")
    month.add_argument("year", type=lambda value: bounded_int(value, 2000, 2100))
    month.add_argument("month", type=lambda value: bounded_int(value, 1, 12))

    country = sub.add_parser("country")
    country.add_argument("country_code")

    sector = sub.add_parser("sector")
    sector.add_argument("sector")

    search = sub.add_parser("search")
    search.add_argument("keyword")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.operation == "search":
        return run_search(args.keyword)

    try:
        path, query, request_meta = build_request(args)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        print_json(
            {
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
            }
        )
        return 2

    if args.operation == "month":
        return run_month(path, request_meta)

    return execute(
        SOURCE,
        BASE_URL,
        path,
        query,
        request_meta,
    )


if __name__ == "__main__":
    raise SystemExit(main())
