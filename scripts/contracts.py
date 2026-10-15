"""
Purpose: define shared semantic contracts used across source adapters, normalization, coverage, status rendering, filtering, and correlation.
When used: imported by deterministic helpers that need canonical event fields or source-state semantics.
Why it exists: prevents divergent field names, state vocabularies, and HTTP classifications from creating cross-layer inconsistencies.
Inputs/parameters: source-state inputs, raw event dictionaries, provenance values, and HTTP status codes.
Outputs: canonical constants plus small pure normalization/classification helpers.
High-level behavior: centralizes the authoritative source-state vocabulary and canonical event field contract while preserving explicit nulls instead of inventing data.
Failure semantics: invalid values are normalized conservatively; callers remain responsible for rejecting unsupported business semantics.
"""
from __future__ import annotations

from typing import Any, Iterable

SOURCE_STATES = {
    "OK",
    "EMPTY",
    "BLOCKED",
    "RATE_LIMITED",
    "UNAVAILABLE",
    "INVALID_RESPONSE",
    "NOT_TESTED",
}

ATTEMPT_STATES = SOURCE_STATES - {"NOT_TESTED"}
FAILURE_STATES = {
    "BLOCKED",
    "RATE_LIMITED",
    "UNAVAILABLE",
    "INVALID_RESPONSE",
}

SOURCE_STATUS_LABELS = {
    "OK": "🟢 OK",
    "EMPTY": "🟡 EMPTY",
    "BLOCKED": "🟠 BLOCKED",
    "RATE_LIMITED": "🟠 RATE LIMITED",
    "UNAVAILABLE": "🔴 UNAVAILABLE",
    "INVALID_RESPONSE": "🔴 INVALID",
    "NOT_TESTED": "⚪ NOT TESTED",
}

BLOCKED_HTTP_STATUSES = {401, 403}
INVALID_HTTP_STATUSES = {400, 404, 405, 410, 422}
RATE_LIMIT_HTTP_STATUSES = {429}

CANONICAL_EVENT_FIELDS = (
    "victim",
    "organization",
    "group",
    "actor",
    "canonical_actor_id",
    "actor_identity_status",
    "date",
    "date_semantics",
    "country",
    "sector",
    "domain",
    "url",
    "data_type",
    "source",
    "provenance",
    "raw_id",
)


def classify_source_state(ok: bool, status: int | None, data: Any) -> str:
    if ok:
        if data in (None, [], {}, ""):
            return "EMPTY"
        if isinstance(data, dict):
            for key in ("results", "victims", "posts", "items", "links", "records"):
                if key in data and data[key] == []:
                    return "EMPTY"
        return "OK"

    if status in BLOCKED_HTTP_STATUSES:
        return "BLOCKED"
    if status in RATE_LIMIT_HTTP_STATUSES:
        return "RATE_LIMITED"
    if status in INVALID_HTTP_STATUSES:
        return "INVALID_RESPONSE"
    return "UNAVAILABLE"


def normalize_provenance(value: Any, fallback_source: str | None = None) -> list[str]:
    items: list[str] = []
    raw_items: Iterable[Any]
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    elif value is None:
        raw_items = ()
    else:
        raw_items = (value,)

    for raw in raw_items:
        text = str(raw or "").strip()
        if text and text not in items:
            items.append(text)

    fallback = str(fallback_source or "").strip()
    if fallback and fallback not in items:
        items.append(fallback)
    return items


def first_nonempty(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None
