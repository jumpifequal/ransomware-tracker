"""
Purpose: shared source-adapter execution wrapper.
When used: called by source-specific REST helpers after argument parsing and request construction.
Why it exists: guarantees consistent JSON envelopes, source states, request traceability, and failure semantics.
Inputs/parameters: source name, base URL, path, optional query, and sanitized request metadata.
Outputs: exactly one JSON object on stdout.
High-level behavior: delegates HTTPS transport, computes a normalized source state, and emits a stable envelope.
Failure semantics: HTTP/network/input failures return ok=false with state BLOCKED, INVALID_RESPONSE, or UNAVAILABLE and a non-zero exit code.
"""
from __future__ import annotations

from typing import Any

from _cli_common import print_json, source_state
from _http_common import SafeRequestError, get


def execute(
    source: str,
    base_url: str,
    path: str,
    query: dict[str, Any] | None,
    request_meta: dict[str, Any],
    profile: str = "api",
) -> int:
    try:
        response = get(base_url, path, query=query, profile=profile)
        data = response["data"]
        payload = {
            "ok": True,
            "state": source_state(True, response["status"], data),
            "source": source,
            "request": request_meta,
            "status": response["status"],
            "data": data,
            "error": None,
        }
        print_json(payload)
        return 0
    except SafeRequestError as exc:
        payload = {
            "ok": False,
            "state": source_state(False, exc.status, None),
            "source": source,
            "request": request_meta,
            "status": exc.status,
            "data": None,
            "error": {
                "type": exc.kind,
                "message": exc.message,
                "status": exc.status,
            },
        }
        print_json(payload)
        return 2
