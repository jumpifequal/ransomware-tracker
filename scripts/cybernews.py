"""
Purpose: retrieve public OSINT content from cybernews through allow-listed HTTPS endpoints.
When used: when API sources need public-reporting fallback or enrichment.
Why it exists: normalizes public page/feed access into the skill's stable JSON source envelope.
Inputs/parameters: CLI operation plus an optional validated search query.
Outputs: exactly one JSON object on stdout containing state, source, request, status, parsed data, and error.
High-level behavior: requests allow-listed pages/feeds, parses RSS or HTML metadata deterministically, and preserves BLOCKED/UNAVAILABLE states.
Failure semantics: access denials such as HTTP 403 become BLOCKED and are not treated as negative evidence.
"""
from __future__ import annotations

import argparse

from _cli_common import print_json, query_text
from _source_runner import execute

BASE_URL = 'https://cybernews.com'
SOURCE = 'cybernews'


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    operation = args.operation
    if operation == "security":
        return '/security/', None, {"operation": operation}
    if operation == "news":
        return '/news/', None, {"operation": operation}
    if operation == "feed":
        return '/feed/', None, {"operation": operation}
    if operation == "search":
        value = query_text(args.query)
        return '/search/', {'q': value}, {"operation": operation, "query": value}
    raise ValueError("unsupported operation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='cybernews.py')
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("security")
    sub.add_parser("news")
    sub.add_parser("feed")
    command = sub.add_parser("search")
    command.add_argument("query")
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

    profile = "rss" if args.operation == "feed" else "html"
    return execute(
        SOURCE,
        BASE_URL,
        path,
        query,
        request_meta,
        profile=profile,
    )


if __name__ == "__main__":
    raise SystemExit(main())
