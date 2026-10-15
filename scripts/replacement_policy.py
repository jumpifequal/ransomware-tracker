"""
Purpose: qualify functional replacement sources and select evidence-preserving fallback ladders.
When used: after primary-source transport failure and before declaring coverage incomplete.
Why it exists: keeps reachability, freshness, functional equivalence, data type, and dataset independence as separate dimensions.
Inputs/parameters: candidate name, required data type, qualification observations, and primary source.
Outputs: machine-readable qualification result or ordered fallback ladder.
High-level behavior: enforces minimum replacement gates and encodes source-specific role/lineage constraints without merging independent and overlapping corroboration.
Failure semantics: candidates failing any required gate remain usable only for narrower roles explicitly supported by their metadata.
"""
from __future__ import annotations

from typing import Any

CANDIDATES: dict[str, dict[str, Any]] = {
    "RansomLook": {
        "roles": {"victim-record", "group-profile", "claim", "history"},
        "independence": "unknown",
        "lineage_note": "treat as distinct surface; do not infer independence without evidence",
    },
    "Ransomnews/Ransomtracker": {
        "roles": {"victim-record", "group-profile", "claim", "history", "aggregate"},
        "independence": "uncertain-overlap",
        "lineage_note": "possible overlap with RansomLook when counts/records closely coincide",
    },
    "Ransomfeed Web/RQL": {
        "roles": {"victim-record", "group-profile", "claim", "history", "aggregate", "structured-filter"},
        "independence": "same-family",
        "lineage_note": "same Ransomfeed family; replacement transport/surface, not independent corroboration",
    },
    "VULONE": {
        "roles": {"victim-record", "group-profile", "claim", "history", "aggregate"},
        "independence": "partial-overlap",
        "lineage_note": "public pages state cross-checking with ransomware.live and RansomLook",
    },
    "ThreatVectr": {
        "roles": {"aggregate", "trend", "ranking"},
        "independence": "derived",
        "lineage_note": "aggregate reports identify ransomware.live-observed claims as underlying dataset",
    },
}

FALLBACKS = {
    "ransomware.live": [
        "ransomware.live:python-api",
        "ransomware.live:web-api",
        "ransomware.live:api-pro",
        "ransomware.live:public-web",
        "Ransomnews/Ransomtracker",
        "RansomLook",
        "VULONE",
        "ThreatVectr",
    ],
    "Ransomfeed": [
        "Ransomfeed:python-api",
        "Ransomfeed:web-api",
        "Ransomfeed Web/RQL",
        "RansomLook",
        "Ransomnews/Ransomtracker",
        "VULONE",
    ],
}


def fallback_ladder(primary: str) -> list[str]:
    try:
        return list(FALLBACKS[primary])
    except KeyError as exc:
        raise ValueError(f"unsupported primary source: {primary}") from exc


def qualify(
    candidate: str,
    required_role: str,
    *,
    reachable: bool,
    content_acquired: bool,
    fresh_enough: bool,
    has_identity_fields: bool,
    history_sufficient: bool,
    reproducible_lookup: bool,
    sample_coherence: bool,
    provenance_declared: bool,
    obsolete_only: bool = False,
    access_control_bypass: bool = False,
) -> dict[str, Any]:
    if candidate not in CANDIDATES:
        raise ValueError(f"unknown candidate: {candidate}")
    meta = CANDIDATES[candidate]
    role_supported = required_role in meta["roles"]

    gates = {
        "reachable": reachable,
        "content_acquired": content_acquired,
        "fresh_enough": fresh_enough,
        "required_role_supported": role_supported,
        "identity_fields": has_identity_fields if required_role in {"victim-record", "claim"} else True,
        "history_sufficient": history_sufficient,
        "reproducible_lookup": reproducible_lookup,
        "sample_coherence": sample_coherence,
        "provenance_declared": provenance_declared,
        "not_obsolete_only": not obsolete_only,
        "no_access_control_bypass": not access_control_bypass,
    }
    qualified = all(gates.values())
    return {
        "candidate": candidate,
        "required_role": required_role,
        "qualified": qualified,
        "gates": gates,
        "independence": meta["independence"],
        "lineage_note": meta["lineage_note"],
    }
