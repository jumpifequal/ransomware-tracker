"""
Purpose: query Ransomfeed's public Web/RQL surface when the direct API transport is unavailable or for cross-checking.
When used: for structured victim/group/country/date/sector lookups and reproducible RQL queries through the public frontend.
Why it exists: preserves Ransomfeed-family functionality when api.ransomfeed.it is blocked by runtime DNS/egress while keeping the channel distinct as Web.
Inputs/parameters: CLI operation plus validated RQL text or structured country/group/sector/year filters.
Outputs: exactly one JSON object on stdout with source state, request metadata, and bounded parsed HTML content.
High-level behavior: builds the documented RQL query, base64-encodes it for the public search page, and retrieves the result page over HTTPS.
Failure semantics: invalid input fails locally; HTTP/network failures remain explicit and never imply that the Ransomfeed API is globally offline.
"""
from __future__ import annotations

import argparse
import base64

from _cli_common import bounded_int, print_json, query_text
from _source_runner import execute

BASE_URL = "https://www.ransomfeed.it"
SOURCE = "ransomfeed-web"


def _encoded_rql(query: str) -> str:
    raw = query_text(query, "rql", 1000)
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def _quote_rql(value: str, label: str) -> str:
    cleaned = query_text(value, label, 200)
    escaped = cleaned.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    operation = args.operation

    if operation == "rql":
        rql = query_text(args.query, "rql", 1000)
    elif operation == "group":
        rql = f"gang:{_quote_rql(args.group, 'group')}"
    elif operation == "country-year":
        country = _quote_rql(args.country, "country")
        year = bounded_int(str(args.year), 2000, 2100)
        rql = (
            f"country:{country} AND date>={year}-01-01 "
            f"AND date<={year}-12-31"
        )
    elif operation == "sector-year":
        sector = _quote_rql(args.sector, "sector")
        year = bounded_int(str(args.year), 2000, 2100)
        rql = (
            f"work_sector~{sector} AND date>={year}-01-01 "
            f"AND date<={year}-12-31"
        )
    elif operation == "victim":
        victim = _quote_rql(args.victim, "victim")
        rql = f"victim~{victim}"
    else:
        raise ValueError("unsupported operation")

    query = {"page": "search-rql", "q": _encoded_rql(rql)}
    return "/", query, {
        "operation": operation,
        "rql": rql,
        "channel": "Web",
        "family": "Ransomfeed",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ransomfeed_web.py")
    sub = parser.add_subparsers(dest="operation", required=True)

    raw = sub.add_parser("rql")
    raw.add_argument("query")

    group = sub.add_parser("group")
    group.add_argument("group")

    cy = sub.add_parser("country-year")
    cy.add_argument("country")
    cy.add_argument("year", type=lambda value: bounded_int(value, 2000, 2100))

    sy = sub.add_parser("sector-year")
    sy.add_argument("sector")
    sy.add_argument("year", type=lambda value: bounded_int(value, 2000, 2100))

    victim = sub.add_parser("victim")
    victim.add_argument("victim")
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

    return execute(
        SOURCE,
        BASE_URL,
        path,
        query,
        meta,
        profile="html",
    )


if __name__ == "__main__":
    raise SystemExit(main())
