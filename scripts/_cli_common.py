"""
Purpose: shared deterministic CLI validation and JSON-envelope helpers.
When used: imported by source-specific REST adapters and deterministic processing adapters.
Why it exists: removes repeated argument-validation and failure-envelope code while keeping behavior explicit.
Inputs/parameters: validated strings, bounded integers, request metadata, and exceptions.
Outputs: encoded path segments, validated numeric values, normalized source states, and JSON envelopes.
High-level behavior: performs small pure validation/normalization operations only.
Failure semantics: raises ValueError or argparse.ArgumentTypeError for invalid local input; never performs network access.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
from typing import Any

from contracts import classify_source_state


def bounded_int(value: str, minimum: int, maximum: int) -> int:
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise argparse.ArgumentTypeError(
            f"value must be between {minimum} and {maximum}"
        )
    return parsed


def path_segment(value: str, label: str, maximum_length: int = 200) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum_length:
        raise argparse.ArgumentTypeError(
            f"{label} must be 1-{maximum_length} characters"
        )
    return urllib.parse.quote(cleaned, safe="")


def query_text(value: str, label: str = "query", maximum_length: int = 300) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum_length:
        raise ValueError(f"{label} must be 1-{maximum_length} characters")
    return cleaned


def source_state(ok: bool, status: int | None, data: Any) -> str:
    return classify_source_state(ok, status, data)


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
