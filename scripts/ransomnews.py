"""
Purpose: query the public Ransomnews Ransomtracker surface as a structured functional replacement/corroboration source.
When used: after ransomware.live transport failure, for group/victim claim context, or during mandatory all-source consultation.
Why it exists: provides current public group profiles, victim listings, dates, and aggregate tracker information without treating it as automatically independent from other trackers.
Inputs/parameters: CLI operation plus validated group name or free-text search term.
Outputs: exactly one JSON object on stdout with parsed HTML metadata and request provenance.
High-level behavior: requests the tracker index or a deterministic group-profile URL using a normalized slug.
Failure semantics: failures remain source/transport evidence only; successful retrieval does not prove dataset independence.
"""
from __future__ import annotations

import argparse
import re

from _cli_common import print_json, query_text
from _source_runner import execute

BASE_URL = "https://ransomnews.com"
SOURCE = "ransomnews"


def _slug(value: str, label: str) -> str:
    cleaned = query_text(value, label, 150).casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    if not slug:
        raise ValueError(f"{label} has no usable slug characters")
    return slug


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    if args.operation == "tracker":
        return "/ransomtracker/", None, {
            "operation": "tracker",
            "data_type": "claims+aggregates",
            "independence": "unknown-possible-overlap",
        }
    if args.operation == "group":
        group = query_text(args.group, "group", 150)
        return f"/ransomtracker/group/{_slug(group, 'group')}/", None, {
            "operation": "group",
            "group": group,
            "data_type": "claim-records+group-profile",
            "independence": "unknown-possible-overlap",
        }
    raise ValueError("unsupported operation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ransomnews.py")
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("tracker")
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
