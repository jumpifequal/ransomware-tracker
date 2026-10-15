"""
Purpose: query current RansomLook API endpoints for posts, groups, leaks, and search.
When used: for recent posts, group intelligence, leak records, and keyword search.
Why it exists: provides portable JSON access to the current RansomLook API while preserving explicit source-state handling.
Inputs/parameters: CLI operation plus validated group, leak, and search values.
Outputs: exactly one JSON object on stdout.
High-level behavior: maps CLI operations to current API paths including /api/recent, /api/groups, and /api/search/.
Failure semantics: invalid input fails locally; remote failures return explicit BLOCKED, INVALID_RESPONSE, or UNAVAILABLE states.
"""
from __future__ import annotations

import argparse

from _cli_common import path_segment, print_json, query_text
from _source_runner import execute

BASE_URL = "https://www.ransomlook.io"
SOURCE = "ransomlook"


def build_request(
    args: argparse.Namespace,
) -> tuple[str, dict[str, object] | None, dict[str, object]]:
    operation = args.operation

    if operation == "recent":
        return "/api/recent", None, {"operation": operation}
    if operation == "groups":
        return "/api/groups", None, {"operation": operation}
    if operation == "group":
        name = path_segment(args.group_name, "group_name")
        return f"/api/group/{name}", None, {
            "operation": operation,
            "group_name": args.group_name,
        }
    if operation == "leaks":
        return "/api/leaks", None, {"operation": operation}
    if operation == "leak":
        leak_id = path_segment(args.leak_id, "leak_id")
        return f"/api/leaks/{leak_id}", None, {
            "operation": operation,
            "leak_id": args.leak_id,
        }
    if operation == "search":
        query_value = query_text(args.query)
        return "/api/search/", {"q": query_value}, {
            "operation": operation,
            "query": query_value,
        }

    raise ValueError("unsupported operation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ransomlook.py")
    sub = parser.add_subparsers(dest="operation", required=True)

    sub.add_parser("recent")
    sub.add_parser("groups")
    sub.add_parser("leaks")

    group = sub.add_parser("group")
    group.add_argument("group_name")

    leak = sub.add_parser("leak")
    leak.add_argument("leak_id")

    search = sub.add_parser("search")
    search.add_argument("query")

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
