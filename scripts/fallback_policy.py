"""
Purpose: summarize source-envelope outcomes and recommend the next retrieval phase without authorizing early completion.
When used: after one retrieval layer (for example direct APIs) and before continuing maximum-effort fallback/replacement coverage.
Why it exists: preserves match/failure semantics while ensuring a successful source never short-circuits mandatory consultation of other relevant sources.
Inputs/parameters: JSON array of source envelopes on stdin.
Outputs: aggregate observation plus next_action=RUN_REMAINING_COVERAGE and completion_authority=coverage_gate.
High-level behavior: records whether usable results exist and classifies failures/empties, but delegates final completeness to coverage_gate.py.
Failure semantics: malformed input returns a structured invalid-input response; this helper never declares final coverage complete.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from _cli_common import print_json
from contracts import ATTEMPT_STATES


def has_records(envelope: dict[str, Any]) -> bool:
    data = envelope.get("data")
    if isinstance(data, list):
        return bool(data)
    if isinstance(data, dict):
        for key in ("results", "victims", "posts", "items", "links", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return bool(value)
        return bool(data)
    return bool(data)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print_json({"ok": False, "error": {"type": "invalid_json", "message": str(exc)}})
        return 2
    if not isinstance(payload, list):
        print_json({"ok": False, "error": {"type": "invalid_input", "message": "input must be an array"}})
        return 2

    states: list[dict[str, Any]] = []
    any_records = False
    for envelope in payload:
        if not isinstance(envelope, dict):
            continue
        state = str(envelope.get("state") or "").upper()
        if state not in ATTEMPT_STATES:
            state = "INVALID_RESPONSE"
        states.append({"source": envelope.get("source"), "state": state})
        if state == "OK" and has_records(envelope):
            any_records = True

    observed = {item["state"] for item in states}
    if any_records:
        aggregate = "MATCH"
        reason = "usable records found; continue remaining relevant source coverage before finalization"
    elif observed and observed == {"EMPTY"}:
        aggregate = "NO_MATCH_CANDIDATE"
        reason = "queried layer returned empty results; final no-match requires coverage-gate completion"
    elif "RATE_LIMITED" in observed:
        aggregate = "RATE_LIMITED"
        reason = "at least one source is rate limited; continue permitted fallback/replacement coverage"
    elif "BLOCKED" in observed:
        aggregate = "PARTIAL_FAILURE"
        reason = "at least one source blocked automated access; continue permitted fallback/replacement coverage"
    elif "INVALID_RESPONSE" in observed:
        aggregate = "PARTIAL_FAILURE"
        reason = "at least one source contract/response was invalid; continue remaining safe coverage"
    else:
        aggregate = "UNAVAILABLE"
        reason = "current retrieval layer returned no usable records; continue remaining safe coverage"

    print_json({
        "ok": True,
        "sources": states,
        "next_action": "RUN_REMAINING_COVERAGE",
        "completion_authority": "coverage_gate",
        "aggregate_state": aggregate,
        "reason": reason,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
