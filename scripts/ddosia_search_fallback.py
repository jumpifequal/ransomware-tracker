"""
Purpose: generate search-engine fallback queries for DDoSia Monitor when direct API and web fetch transports are blocked.
When used: after DDoSia API/Web→API/public-page fetch attempts fail because of runtime egress, proxy, robots, TLS, DNS, or timeout restrictions.
Why it exists: ChatGPT/Claude search backends may still expose freshly indexed DDoSia pages even when direct fetch transports cannot reach ddosia.rfeed.it.
Inputs/parameters: query kind plus optional country, month, host, or date.
Outputs: JSON containing ordered search queries and the required interpretation policy.
High-level behavior: builds domain-restricted searches for the DDoSia dashboard/search/calendar pages and broader corroboration searches without pretending indexed snippets are a complete live API response.
Failure semantics: invalid parameters fail locally; search results must still be freshness- and scope-qualified by the host model before use.
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

DOMAIN = "ddosia.rfeed.it"


def _country_terms(country: str) -> list[str]:
    value = " ".join(country.split())
    if not value:
        raise ValueError("country is required")
    aliases = [value]
    if value.casefold() in {"italy", "italia", "it"}:
        aliases.extend(["Italy", "Italia", "IT"])
    return list(dict.fromkeys(aliases))


def _month(value: str) -> str:
    cleaned = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}", cleaned):
        raise ValueError("month must be YYYY-MM")
    return cleaned


def build_queries(
    kind: str,
    *,
    country: str | None = None,
    month: str | None = None,
    host: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    kind = kind.strip().casefold()
    queries: list[str] = []

    if kind == "country-month":
        if not country or not month:
            raise ValueError("country and month are required")
        month_value = _month(month)
        for term in _country_terms(country):
            queries.extend([
                f'site:{DOMAIN} "{term}" "{month_value}" "DDoSia Monitor"',
                f'site:{DOMAIN}/index.php "{term}" "{month_value}"',
                f'site:{DOMAIN}/search.php "{term}" "{month_value}"',
            ])
        queries.append(f'"DDoSia" "{country}" "{month_value}" NoName057')

    elif kind == "host":
        value = " ".join((host or "").split())
        if not value:
            raise ValueError("host is required")
        queries.extend([
            f'site:{DOMAIN}/search.php "{value}"',
            f'site:{DOMAIN} "{value}" "DDoSia Monitor"',
            f'"{value}" DDoSia NoName057',
        ])

    elif kind == "date":
        value = (date or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("date must be YYYY-MM-DD")
        queries.extend([
            f'site:{DOMAIN} "{value}" "DDoSia Monitor"',
            f'site:{DOMAIN}/calendar.php "{value}"',
            f'"DDoSia" "{value}" NoName057',
        ])

    elif kind == "recent":
        queries.extend([
            f'site:{DOMAIN}/index.php "Last 24 hours" "DDoSia"',
            f'site:{DOMAIN} "DDoSia Target Monitoring" "Updated"',
            f'"DDoSia" NoName057 recent targets',
        ])

    else:
        raise ValueError("unsupported kind")

    return {
        "kind": kind,
        "queries": list(dict.fromkeys(queries)),
        "channel": "Search index",
        "policy": {
            "source_identity": "DDoSia Monitor when the indexed result is a ddosia.rfeed.it page",
            "freshness_required": True,
            "do_not_claim_complete_period": True,
            "direct_transport_state_preserved": True,
            "semantic_unit": "DDoS target observation",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="kind", required=True)

    cm = sub.add_parser("country-month")
    cm.add_argument("country")
    cm.add_argument("month")

    host = sub.add_parser("host")
    host.add_argument("host")

    date = sub.add_parser("date")
    date.add_argument("date")

    sub.add_parser("recent")

    args = parser.parse_args()
    try:
        if args.kind == "country-month":
            result = build_queries("country-month", country=args.country, month=args.month)
        elif args.kind == "host":
            result = build_queries("host", host=args.host)
        elif args.kind == "date":
            result = build_queries("date", date=args.date)
        else:
            result = build_queries("recent")
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
