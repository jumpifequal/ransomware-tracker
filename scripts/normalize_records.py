"""
Purpose: normalize heterogeneous live-source records into one canonical event schema.
When used: after a source helper returns successful JSON and before filtering, deduplication, or correlation.
Why it exists: guarantees that live and historical records expose the same semantic fields instead of parallel published_at/record_type versus date/data_type contracts.
Inputs/parameters: --source plus a JSON object/array read from stdin.
Outputs: JSON with canonical records containing victim/organization, group/actor identity fields, date/date_semantics, domain/url, data_type, source, provenance, and raw_id.
High-level behavior: unwraps known source envelopes, maps source-specific fields conservatively, separates domain from URL, and preserves provenance without inventing missing values.
Failure semantics: malformed JSON or unsupported structures return ok=false and a non-zero exit code.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _cli_common import print_json
from contracts import first_nonempty, normalize_provenance

EDITORIAL_SOURCES = {
    "bleepingcomputer",
    "cybernews",
    "securityaffairs",
    "databreaches",
}

DATE_CANDIDATES = (
    ("date", "source_date"),
    ("claim_date", "claim_date"),
    ("attackdate", "attack_date"),
    ("discovered", "discovery_date"),
    ("published_at", "publication_date"),
    ("published", "publication_date"),
    ("pubDate", "publication_date"),
    ("detected_at", "detected_at"),
    ("timestamp", "timestamp"),
)


def as_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    data = payload.get("data", payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    for key in ("results", "victims", "posts", "items", "links", "records"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _date_value(item: dict[str, Any]) -> tuple[str | None, str | None]:
    for key, semantics in DATE_CANDIDATES:
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip(), semantics
    return None, None


def canonical(source: str, item: dict[str, Any]) -> dict[str, Any]:
    victim = first_nonempty(item, "victim", "name", "post_name", "title")
    organization = first_nonempty(item, "organization", "org_name")
    group = first_nonempty(item, "group", "gang", "group_name")
    actor = first_nonempty(item, "actor", "threat_actor", "campaign_actor")
    date, date_semantics = _date_value(item)
    country = item.get("country")
    sector = first_nonempty(item, "sector", "work_sector")
    domain = first_nonempty(item, "domain", "website", "host")
    url = first_nonempty(item, "url", "link", "claim_url", "canonical")

    data_type = item.get("data_type")
    if not data_type:
        data_type = "media-report" if source in EDITORIAL_SOURCES else "ransomware-claim-record"

    return {
        "victim": str(victim).strip() if victim is not None else None,
        "organization": str(organization).strip() if organization is not None else None,
        "group": str(group).strip() if group is not None else None,
        "actor": str(actor).strip() if actor is not None else None,
        "canonical_actor_id": item.get("canonical_actor_id"),
        "actor_identity_status": item.get("actor_identity_status"),
        "date": date,
        "date_semantics": item.get("date_semantics") or date_semantics,
        "country": str(country).strip() if country is not None else None,
        "sector": str(sector).strip() if sector is not None else None,
        "domain": str(domain).strip() if domain is not None else None,
        "url": str(url).strip() if url is not None else None,
        "data_type": str(data_type).strip(),
        "source": source,
        "provenance": normalize_provenance(item.get("provenance"), source),
        "raw_id": first_nonempty(item, "raw_id", "id", "event_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="normalize_records.py")
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print_json({"ok": False, "error": {"type": "invalid_json", "message": str(exc)}})
        return 2

    records = [canonical(args.source, item) for item in as_records(payload)]
    print_json({"ok": True, "source": args.source, "count": len(records), "records": records})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
