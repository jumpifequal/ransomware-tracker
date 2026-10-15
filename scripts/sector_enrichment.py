"""
Purpose: prepare and validate conditional web-based sector enrichment for victim records missing sector data.
When used: only when the user request materially requires sector information and the victim name is known but the sector is absent.
Why it exists: enables targeted sector recovery from public web evidence without guessing, over-enriching unrelated requests, or confusing identity evidence with sector evidence.
Inputs/parameters: victim name, optional country/organization/domain/context, and candidate evidence records produced by host-native web search/fetch.
Outputs: deterministic search queries plus a validated sector decision containing source provenance and confidence.
High-level behavior: builds narrow public-web queries, requires identity disambiguation for natural persons, prefers explicit first-party/authoritative sector evidence, and rejects ambiguous or inferred-only matches.
Failure semantics: when evidence is insufficient, conflicting, ambiguous, or not clearly tied to the victim, returns sector=None rather than inventing a classification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AUTHORITATIVE_TYPES = {
    "official-site",
    "employer-site",
    "company-registry",
    "professional-registry",
    "government",
}

ACCEPTABLE_TYPES = AUTHORITATIVE_TYPES | {
    "reputable-media",
    "industry-directory",
}


@dataclass(frozen=True)
class SectorDecision:
    sector: str | None
    confidence: str
    reason: str
    source_url: str | None = None
    source_type: str | None = None


def needs_sector_enrichment(
    sector: str | None,
    *,
    request_requires_sector: bool,
    victim_name: str | None,
) -> bool:
    return (
        request_requires_sector
        and not (sector or "").strip()
        and bool((victim_name or "").strip())
    )


def build_queries(
    victim_name: str,
    *,
    country: str | None = None,
    organization: str | None = None,
    domain: str | None = None,
) -> list[str]:
    name = " ".join(victim_name.split())
    if not name:
        raise ValueError("victim_name is required")

    context = [x.strip() for x in (organization, domain, country) if x and x.strip()]
    suffix = " ".join(context)

    queries = [
        f'"{name}" sector industry',
        f'"{name}" company organization sector',
    ]
    if suffix:
        queries.insert(0, f'"{name}" {suffix} sector')
        queries.append(f'"{name}" {suffix} industry')

    # Keep stable order while deduplicating.
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def evaluate_evidence(
    evidence: list[dict[str, Any]],
    *,
    natural_person: bool,
) -> SectorDecision:
    valid: list[dict[str, Any]] = []

    for item in evidence:
        sector = _normalized(item.get("sector"))
        source_url = _normalized(item.get("source_url"))
        source_type = _normalized(item.get("source_type"))
        identity_match = bool(item.get("identity_match"))
        explicit_sector = bool(item.get("explicit_sector"))
        public_source = bool(item.get("public_source", True))

        if not sector or not source_url or source_type not in ACCEPTABLE_TYPES:
            continue
        if not public_source or not identity_match or not explicit_sector:
            continue

        # Natural persons require an additional disambiguation signal.
        if natural_person and not bool(item.get("person_disambiguated")):
            continue

        valid.append(item)

    if not valid:
        return SectorDecision(
            sector=None,
            confidence="none",
            reason="no sufficiently attributable public sector evidence",
        )

    # Prefer authoritative sources, then corroboration.
    authoritative = [
        x for x in valid if _normalized(x.get("source_type")) in AUTHORITATIVE_TYPES
    ]
    pool = authoritative or valid

    by_sector: dict[str, list[dict[str, Any]]] = {}
    for item in pool:
        sector = _normalized(item.get("sector"))
        by_sector.setdefault(sector.casefold(), []).append(item)

    if len(by_sector) > 1:
        return SectorDecision(
            sector=None,
            confidence="conflict",
            reason="conflicting sector evidence",
        )

    chosen_items = next(iter(by_sector.values()))
    chosen = chosen_items[0]
    sector = _normalized(chosen.get("sector"))
    confidence = "high" if authoritative or len(chosen_items) >= 2 else "medium"

    return SectorDecision(
        sector=sector,
        confidence=confidence,
        reason="explicit public evidence matched to victim identity",
        source_url=_normalized(chosen.get("source_url")),
        source_type=_normalized(chosen.get("source_type")),
    )
