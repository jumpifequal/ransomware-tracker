"""
Purpose: validate and normalize per-source status rows from current-run evidence.
When used: immediately before rendering the mandatory source-status footer.
Why it exists: prevents unqueried sources from being mislabeled as unavailable or otherwise assigned unsupported states.
Inputs/parameters: JSON array on stdin; each item describes source, attempted flag, optional state, channel, note, and evidence.
Outputs: JSON array of validated footer rows with normalized labels.
High-level behavior: enforces that operational states require an actual current-run attempt and minimum evidence; unattempted material sources become NOT_TESTED.
Failure semantics: exits non-zero with a structured error when a requested state is not supported by the supplied evidence.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from contracts import ATTEMPT_STATES, FAILURE_STATES, SOURCE_STATUS_LABELS

LABELS = SOURCE_STATUS_LABELS


def _has_failure_evidence(state: str, evidence: dict[str, Any]) -> bool:
    status = evidence.get("http_status")
    error_type = str(evidence.get("error_type") or "").strip()
    error_message = str(evidence.get("error_message") or "").strip()

    if state == "BLOCKED":
        return status == 403
    if state == "RATE_LIMITED":
        return status == 429
    if state in {"INVALID", "INVALID_RESPONSE"}:
        return status in {400, 404, 405, 410, 422} or bool(evidence.get("contract_error"))
    if state == "UNAVAILABLE":
        return (
            isinstance(status, int) and 500 <= status <= 599
        ) or bool(error_type or error_message)
    return True


def normalize_row(item: dict[str, Any]) -> dict[str, str] | None:
    source = str(item.get("source") or "").strip()
    if not source:
        raise ValueError("source is required")

    attempted = bool(item.get("attempted"))
    material = bool(item.get("material_omission"))
    state = str(item.get("state") or "").strip().upper()
    channel = str(item.get("channel") or "").strip()
    note = str(item.get("note") or "").strip()
    evidence = item.get("evidence") or {}

    if not attempted:
        if state and state != "NOT_TESTED":
            raise ValueError(f"{source}: unattempted source cannot be {state}")
        if not material:
            return None
        return {
            "Source": source,
            "Status": LABELS["NOT_TESTED"],
            "Channel": channel or "—",
            "Note": note or "not queried in current run",
        }

    if state not in ATTEMPT_STATES:
        raise ValueError(f"{source}: attempted source requires a supported state")

    if state in FAILURE_STATES and not _has_failure_evidence(state, evidence):
        raise ValueError(f"{source}: {state} lacks current-run failure evidence")

    if state == "OK" and not evidence.get("success"):
        raise ValueError(f"{source}: OK requires success evidence")

    if state == "EMPTY" and not evidence.get("success"):
        raise ValueError(f"{source}: EMPTY requires successful-request evidence")

    return {
        "Source": source,
        "Status": LABELS[state],
        "Channel": channel or "—",
        "Note": note or "current-run evidence recorded",
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, list):
            raise ValueError("input must be a JSON array")
        rows = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("each source ledger item must be an object")
            row = normalize_row(item)
            if row is not None:
                rows.append(row)
        print(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": {"type": "invalid_source_ledger", "message": str(exc)}},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
