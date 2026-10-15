"""
Purpose: enforce exhaustive maximum-effort coverage for the threat-family scope selected by the request.
When used: immediately before rendering unrestricted ransomware, DDoS, breach, or mixed operational responses.
Why it exists: prevents early exit and makes the coverage gate, not an individual successful source, the only deterministic completion authority.
Inputs/parameters: JSON array on stdin; each item describes source, attempted flag, state, attempted_paths, available_paths, and exhausted flag.
Outputs: JSON with ok=true and required-source summary, or ok=false with concrete coverage gaps.
High-level behavior: requires every source relevant to the selected scope to be present, attempted, and either successful/empty or exhausted across all safe available paths.
Failure semantics: exits non-zero when a relevant source is missing, unattempted, non-terminal, or still has an untried safe retrieval path.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from contracts import ATTEMPT_STATES

RANSOMWARE_SOURCES = [
    "ransomware.live",
    "Ransomfeed",
    "Ransomfeed Web/RQL",
    "RansomLook",
    "Ransomnews/Ransomtracker",
    "VULONE",
    "ThreatVectr",
    "BleepingComputer",
    "Cybernews",
    "Security Affairs",
]
DDOS_SOURCES = ["DDoSia Monitor"]
BREACH_SOURCES = [
    "DataBreaches.net",
    "Have I Been Pwned",
    "California AG",
    "HHS OCR",
    "SEC EDGAR Item 1.05",
    "BleepingComputer",
    "Cybernews",
    "Security Affairs",
]


def _union(*groups: list[str]) -> list[str]:
    return list(dict.fromkeys(item for group in groups for item in group))


CONFIGURED_SOURCES = _union(RANSOMWARE_SOURCES, DDOS_SOURCES, BREACH_SOURCES)


def required_sources(scope: str = "ransomware") -> list[str]:
    normalized = scope.strip().casefold()
    if normalized == "ransomware":
        return list(RANSOMWARE_SOURCES)
    if normalized == "ddos":
        return list(DDOS_SOURCES)
    if normalized == "breach":
        return list(BREACH_SOURCES)
    if normalized in {"mixed", "ransomware_ddos"}:
        return _union(RANSOMWARE_SOURCES, DDOS_SOURCES)
    if normalized == "ransomware_breach":
        return _union(RANSOMWARE_SOURCES, BREACH_SOURCES)
    if normalized == "ddos_breach":
        return _union(DDOS_SOURCES, BREACH_SOURCES)
    if normalized == "all":
        return list(CONFIGURED_SOURCES)
    raise ValueError(f"unsupported coverage scope: {scope}")


def validate_coverage(items: list[dict[str, Any]], scope: str = "ransomware") -> dict[str, Any]:
    by_source = {
        str(item.get("source") or "").strip(): item
        for item in items
        if isinstance(item, dict) and str(item.get("source") or "").strip()
    }
    gaps: list[dict[str, Any]] = []
    required = required_sources(scope)

    for source in required:
        item = by_source.get(source)
        if item is None:
            gaps.append({"source": source, "reason": "missing ledger entry"})
            continue
        if not bool(item.get("attempted")):
            gaps.append({"source": source, "reason": "source not attempted"})
            continue

        state = str(item.get("state") or "").strip().upper()
        if state not in ATTEMPT_STATES:
            gaps.append({"source": source, "reason": f"non-terminal state: {state or 'missing'}"})
            continue

        available = [str(x) for x in (item.get("available_paths") or [])]
        attempted = [str(x) for x in (item.get("attempted_paths") or [])]
        untried = [path for path in available if path not in attempted]
        if untried:
            gaps.append({"source": source, "reason": "safe retrieval paths remain", "untried_paths": untried})
            continue

        if state not in {"OK", "EMPTY"} and not bool(item.get("exhausted")):
            gaps.append({"source": source, "reason": "terminal non-success without exhaustion evidence"})

    return {"ok": not gaps, "scope": scope, "required_sources": required, "gaps": gaps}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, list):
            raise ValueError("input must be a JSON array")
        scope = "ransomware"
        if payload and isinstance(payload[0], dict) and payload[0].get("_coverage_scope"):
            scope = str(payload[0]["_coverage_scope"])
            payload = [item for item in payload if "_coverage_scope" not in item]
        result = validate_coverage(payload, scope=scope)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0 if result["ok"] else 3
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": {"type": "invalid_coverage_ledger", "message": str(exc)}}, ensure_ascii=False, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
