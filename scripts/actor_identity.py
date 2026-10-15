"""
Purpose: resolve threat-actor aliases conservatively from caller-supplied evidence and detect same-name collisions before cross-source merging or correlation.
When used: before actor/group normalization, victim deduplication by actor, and cross-threat searches where aliases or homonyms could fragment or falsely merge threat entities.
Why it exists: exact-name equality does not prove identity, while vendor-specific aliases can refer to one actor under different names; runtime logic must remain generic rather than hard-code a few known actors.
Inputs/parameters: actor records supplied by the caller, actor name, and optional threat-family hints.
Outputs: JSON-compatible resolution/comparison records with canonical actor id/name, relation class, family/operation context, confidence, and collision details.
High-level behavior: normalizes names, resolves only explicit verified aliases from supplied records, uses family context only to disambiguate, and refuses fuzzy or unsupported merges.
Failure semantics: unknown names remain UNRESOLVED; ambiguous names become ENTITY_COLLISION; malformed or unverified records are ignored rather than promoted to identity evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from typing import Any


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def _normalize_family(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or None


def _validated_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for raw in records:
        if not isinstance(raw, dict):
            continue
        actor_id = str(raw.get("actor_id") or "").strip()
        canonical_name = str(raw.get("canonical_name") or "").strip()
        verified = raw.get("verified") is True
        if not actor_id or not canonical_name or not verified:
            continue

        aliases_raw = raw.get("aliases") or []
        families_raw = raw.get("threat_families") or []
        operations_raw = raw.get("operation_types") or []

        aliases = [str(v).strip() for v in aliases_raw if str(v).strip()]
        families = [_normalize_family(str(v)) for v in families_raw if str(v).strip()]
        operations = [_normalize_family(str(v)) for v in operations_raw if str(v).strip()]

        validated.append({
            "actor_id": actor_id,
            "canonical_name": canonical_name,
            "aliases": aliases,
            "threat_families": [v for v in families if v],
            "operation_types": [v for v in operations if v],
            "alias_confidence": str(raw.get("alias_confidence") or "UNSPECIFIED").upper(),
            "evidence": raw.get("evidence"),
            "notes": raw.get("notes"),
            "verified": True,
        })
    return validated


def _record_names(record: dict[str, Any]) -> list[str]:
    return [record["canonical_name"], *record.get("aliases", [])]


def _name_match(record: dict[str, Any], query: str) -> bool:
    needle = normalize_name(query)
    return any(normalize_name(name) == needle for name in _record_names(record))


def _family_match(record: dict[str, Any], family: str | None) -> bool:
    normalized = _normalize_family(family)
    if normalized is None:
        return True
    return normalized in set(record.get("threat_families", []))


def resolve(
    name: str,
    records: list[dict[str, Any]],
    family: str | None = None,
) -> dict[str, Any]:
    query = (name or "").strip()
    if not query:
        raise ValueError("actor name is required")

    catalogue = _validated_records(records)
    name_matches = [record for record in catalogue if _name_match(record, query)]
    family_matches = [record for record in name_matches if _family_match(record, family)]

    if family and len(family_matches) == 1:
        return {
            "status": "RESOLVED_ALIAS",
            "query": query,
            "family_hint": family,
            **family_matches[0],
        }

    if family and len(name_matches) == 1 and not family_matches:
        return {
            "status": "FAMILY_MISMATCH",
            "query": query,
            "family_hint": family,
            "candidate": name_matches[0],
            "merge_allowed": False,
            "reason": "verified actor name exists but supplied threat-family hint conflicts with that record",
        }

    if len(name_matches) == 1:
        return {
            "status": "RESOLVED_ALIAS",
            "query": query,
            "family_hint": family,
            **name_matches[0],
        }

    if len(name_matches) > 1:
        return {
            "status": "ENTITY_COLLISION",
            "query": query,
            "family_hint": family,
            "candidates": name_matches,
            "merge_allowed": False,
            "reason": "same normalized name maps to multiple verified threat entities",
        }

    return {
        "status": "UNRESOLVED",
        "query": query,
        "family_hint": family,
        "canonical_name": query,
        "merge_allowed": False,
        "reason": "no verified alias mapping in supplied evidence; preserve source label",
    }


def same_actor(
    left: str,
    right: str,
    records: list[dict[str, Any]],
    left_family: str | None = None,
    right_family: str | None = None,
) -> dict[str, Any]:
    left_result = resolve(left, records, left_family)
    right_result = resolve(right, records, right_family)

    if (
        left_result["status"] == "RESOLVED_ALIAS"
        and right_result["status"] == "RESOLVED_ALIAS"
    ):
        same = left_result["actor_id"] == right_result["actor_id"]
        return {
            "same_actor": same,
            "relation": "VERIFIED_ALIAS_SET" if same else "DISTINCT_ENTITY",
            "left": left_result,
            "right": right_result,
        }

    collision = (
        left_result["status"] == "ENTITY_COLLISION"
        or right_result["status"] == "ENTITY_COLLISION"
    )
    return {
        "same_actor": False,
        "relation": "ENTITY_COLLISION" if collision else "UNVERIFIED",
        "left": left_result,
        "right": right_result,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="actor_identity.py")
    parser.add_argument(
        "operation",
        choices=("resolve", "compare"),
        help="Read JSON evidence from stdin and resolve or compare actor labels.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("stdin payload must be a JSON object")
        records = payload.get("records")
        if not isinstance(records, list):
            raise ValueError("records must be a JSON array")

        if args.operation == "resolve":
            result = resolve(
                str(payload.get("name") or ""),
                records,
                payload.get("family"),
            )
        else:
            result = same_actor(
                str(payload.get("left") or ""),
                str(payload.get("right") or ""),
                records,
                payload.get("left_family"),
                payload.get("right_family"),
            )
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
