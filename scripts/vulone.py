"""
Purpose: query VULONE public ransomware group/victimology pages as a tertiary corroboration source.
When used: during all-source consultation and as a third-line check after primary/secondary claim sources.
Why it exists: VULONE exposes structured group, victim, date, geography, and aggregate information but may have uneven freshness and partially overlapping lineage.
Inputs/parameters: CLI operation plus validated group name.
Outputs: exactly one JSON object on stdout with bounded parsed HTML content and lineage metadata.
High-level behavior: retrieves the ransomware research index or deterministic group profile URL.
Failure semantics: a successful page is not accepted as fresh automatically; freshness must be evaluated against the requested period before using records.
"""
from __future__ import annotations

import argparse
import re

from _cli_common import print_json, query_text
from _source_runner import execute

BASE_URL = "https://vulone.com"
SOURCE = "vulone"


def _slug(value: str) -> str:
    cleaned = query_text(value, "group", 150).casefold()
    slug = re.sub(r"[^a-z0-9]+", "", cleaned)
    if not slug:
        raise ValueError("group has no usable slug characters")
    return slug


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    if args.operation == "groups":
        return "/ransomware-research", None, {
            "operation": "groups",
            "data_type": "groups+aggregates",
            "independence": "partial-cross-check-lineage",
        }
    if args.operation == "group":
        group = query_text(args.group, "group", 150)
        return f"/ransomware/{_slug(group)}", None, {
            "operation": "group",
            "group": group,
            "data_type": "claim-records+group-profile",
            "independence": "partial-cross-check-lineage",
        }
    raise ValueError("unsupported operation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vulone.py")
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("groups")
    group = sub.add_parser("group")
    group.add_argument("group")
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
