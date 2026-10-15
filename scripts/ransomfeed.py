"""
Purpose: query the current Ransomfeed public filter API.
When used: for victim search, country/gang/year filtering, recent records, and combined filters.
Why it exists: replaces obsolete /v1/victims assumptions with the current path-composable Ransomfeed API.
Inputs/parameters: CLI operation plus validated query, country, gang, year, and result-limit values.
Outputs: exactly one JSON object on stdout with normalized source state and data.
High-level behavior: constructs current documented filter paths such as /search/{term}, /country/{country}, /gang/{gang}, /date/{year}, and /offset/{limit}.
Failure semantics: invalid local input fails before network access; remote errors return machine-readable JSON with explicit source state.
"""
from __future__ import annotations

import argparse

from _cli_common import bounded_int, path_segment, print_json, query_text
from _source_runner import execute

BASE_URL = "https://api.ransomfeed.it"
SOURCE = "ransomfeed"


def _with_limit(path: str, limit: int | None) -> str:
    if limit is None:
        return path
    return f"{path.rstrip('/')}/offset/{limit}"


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    operation = args.operation

    if operation == "recent":
        limit = args.limit
        return f"/offset/{limit}", None, {
            "operation": operation,
            "limit": limit,
        }

    if operation == "search":
        term = query_text(args.keyword, "keyword")
        path = f"/search/{path_segment(term, 'keyword', 300)}"
        return _with_limit(path, args.limit), None, {
            "operation": operation,
            "keyword": term,
            "limit": args.limit,
        }

    if operation == "country":
        country = query_text(args.country, "country", 100)
        path = f"/country/{path_segment(country, 'country', 100)}"
        return _with_limit(path, args.limit), None, {
            "operation": operation,
            "country": country,
            "limit": args.limit,
        }

    if operation == "gang":
        gang = query_text(args.gang, "gang", 100)
        path = f"/gang/{path_segment(gang, 'gang', 100)}"
        return _with_limit(path, args.limit), None, {
            "operation": operation,
            "gang": gang,
            "limit": args.limit,
        }

    if operation == "year":
        path = f"/date/{args.year}"
        return _with_limit(path, args.limit), None, {
            "operation": operation,
            "year": args.year,
            "limit": args.limit,
        }

    if operation == "combined":
        parts: list[str] = []
        request_meta: dict[str, object] = {"operation": operation}

        if args.keyword:
            term = query_text(args.keyword, "keyword")
            parts.extend(["search", path_segment(term, "keyword", 300)])
            request_meta["keyword"] = term
        if args.country:
            country = query_text(args.country, "country", 100)
            parts.extend(["country", path_segment(country, "country", 100)])
            request_meta["country"] = country
        if args.gang:
            gang = query_text(args.gang, "gang", 100)
            parts.extend(["gang", path_segment(gang, "gang", 100)])
            request_meta["gang"] = gang
        if args.year:
            parts.extend(["date", str(args.year)])
            request_meta["year"] = args.year

        if not parts:
            raise ValueError("combined requires at least one filter")

        path = "/" + "/".join(parts)
        path = _with_limit(path, args.limit)
        request_meta["limit"] = args.limit
        return path, None, request_meta

    raise ValueError("unsupported operation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ransomfeed.py")
    sub = parser.add_subparsers(dest="operation", required=True)

    recent = sub.add_parser("recent")
    recent.add_argument(
        "--limit",
        type=lambda value: bounded_int(value, 1, 1000),
        default=100,
    )

    search = sub.add_parser("search")
    search.add_argument("keyword")
    search.add_argument(
        "--limit",
        type=lambda value: bounded_int(value, 1, 1000),
        default=100,
    )

    country = sub.add_parser("country")
    country.add_argument("country")
    country.add_argument(
        "--limit",
        type=lambda value: bounded_int(value, 1, 1000),
        default=100,
    )

    gang = sub.add_parser("gang")
    gang.add_argument("gang")
    gang.add_argument(
        "--limit",
        type=lambda value: bounded_int(value, 1, 1000),
        default=100,
    )

    year = sub.add_parser("year")
    year.add_argument("year", type=lambda value: bounded_int(value, 2000, 2100))
    year.add_argument(
        "--limit",
        type=lambda value: bounded_int(value, 1, 1000),
        default=100,
    )

    combined = sub.add_parser("combined")
    combined.add_argument("--keyword")
    combined.add_argument("--country")
    combined.add_argument("--gang")
    combined.add_argument(
        "--year",
        type=lambda value: bounded_int(value, 2000, 2100),
    )
    combined.add_argument(
        "--limit",
        type=lambda value: bounded_int(value, 1, 1000),
        default=100,
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

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

    return execute(
        SOURCE,
        BASE_URL,
        path,
        query,
        request_meta,
    )


if __name__ == "__main__":
    raise SystemExit(main())
