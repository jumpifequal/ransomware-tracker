"""
Purpose: deterministically filter and deduplicate canonical event records.
When used: after normalize_records.py and before final interpretation or cross-correlation.
Why it exists: applies one date/domain/provenance contract across live and historical claim-like records.
Inputs/parameters: canonical JSON records from stdin plus optional keyword, country, date-from, and date-to filters.
Outputs: JSON containing filtered canonical records with merged provenance.
High-level behavior: filters using canonical date and domain fields, deduplicates by victim/group/date, and unions corroborating provenance while preserving the first primary source.
Failure semantics: malformed input returns ok=false; ambiguous or missing fields are never invented.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from typing import Any

from _cli_common import print_json
from contracts import normalize_provenance


def normalized_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def date_prefix(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) >= 10:
        candidate = text[:10]
        try:
            datetime.strptime(candidate, "%Y-%m-%d")
            return candidate
        except ValueError:
            return None
    return None


def matches(
    record: dict[str, Any],
    keyword: str | None,
    country: str | None,
    date_from: str | None,
    date_to: str | None,
) -> bool:
    if keyword:
        needle = normalized_text(keyword)
        haystack = " ".join(
            normalized_text(record.get(field))
            for field in ("victim", "organization", "group", "actor", "domain", "url", "sector")
        )
        if needle not in haystack:
            return False

    if country and normalized_text(record.get("country")) != normalized_text(country):
        return False

    record_date = date_prefix(record.get("date"))
    if date_from and (record_date is None or record_date < date_from):
        return False
    if date_to and (record_date is None or record_date > date_to):
        return False
    return True


def dedupe_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalized_text(record.get("victim") or record.get("organization")),
        normalized_text(record.get("group") or record.get("canonical_actor_id")),
        date_prefix(record.get("date")) or "",
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="filter_records.py")
    parser.add_argument("--keyword")
    parser.add_argument("--country")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print_json({"ok": False, "error": {"type": "invalid_json", "message": str(exc)}})
        return 2

    records = payload.get("records", payload)
    if not isinstance(records, list):
        print_json({"ok": False, "error": {"type": "invalid_input", "message": "records must be a JSON array"}})
        return 2

    selected = [
        record for record in records
        if isinstance(record, dict)
        and matches(record, args.keyword, args.country, args.date_from, args.date_to)
    ]

    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in selected:
        key = dedupe_key(record)
        existing = merged.get(key)
        if existing is None:
            copy = dict(record)
            copy["provenance"] = normalize_provenance(copy.get("provenance"), copy.get("source"))
            merged[key] = copy
            continue

        existing["provenance"] = normalize_provenance(
            [*existing.get("provenance", []), *normalize_provenance(record.get("provenance"), record.get("source"))]
        )
        for field in ("country", "sector", "domain", "url", "canonical_actor_id", "actor_identity_status"):
            if not existing.get(field) and record.get(field):
                existing[field] = record[field]

    output = list(merged.values())
    print_json({
        "ok": True,
        "count": len(output),
        "records": output,
        "filters": {
            "keyword": args.keyword,
            "country": args.country,
            "date_from": args.date_from,
            "date_to": args.date_to,
        },
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
