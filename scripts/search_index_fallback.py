"""
Purpose: generate source-specific search-index recovery queries when direct API, Web→API, feed, or public-page transports are blocked.
When used: after supported direct transports for a configured live source fail because of runtime egress, proxy, robots, DNS, TLS, or timeout restrictions.
Why it exists: ChatGPT/Claude search backends can expose fresh indexed source content even when direct fetch cannot reach the source domain.
Inputs/parameters: source name, query kind, and optional victim/group/country/sector/host/date/month/free-text values.
Outputs: JSON containing ordered search queries, source/domain metadata, freshness expectations, semantic unit, and completeness policy.
High-level behavior: applies declarative source profiles and stable query templates without treating indexed snippets as a complete substitute for the canonical source.
Failure semantics: unsupported sources/kinds or missing parameters fail locally; indexed evidence must still be freshness-, attribution-, and completeness-qualified before use.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceProfile:
    key: str
    name: str
    domain: str
    semantic_unit: str
    editorial: bool = False
    aggregate_only: bool = False


PROFILES: dict[str, SourceProfile] = {
    "ransomware.live": SourceProfile(
        "ransomware.live", "ransomware.live", "ransomware.live", "ransomware claim/victim record"
    ),
    "ransomfeed": SourceProfile(
        "ransomfeed", "Ransomfeed", "ransomfeed.it", "ransomware claim/victim record"
    ),
    "ransomlook": SourceProfile(
        "ransomlook", "RansomLook", "ransomlook.io", "ransomware claim/victim record"
    ),
    "ransomnews": SourceProfile(
        "ransomnews", "Ransomnews/Ransomtracker", "ransomnews.com", "ransomware claim/victim record"
    ),
    "vulone": SourceProfile(
        "vulone", "VULONE", "vulone.com", "ransomware corroboration record"
    ),
    "threatvectr": SourceProfile(
        "threatvectr", "ThreatVectr", "threatvectr.com", "ransomware aggregate statistic",
        aggregate_only=True,
    ),
    "bleepingcomputer": SourceProfile(
        "bleepingcomputer", "BleepingComputer", "bleepingcomputer.com", "media report", editorial=True
    ),
    "cybernews": SourceProfile(
        "cybernews", "Cybernews", "cybernews.com", "media report", editorial=True
    ),
    "securityaffairs": SourceProfile(
        "securityaffairs", "Security Affairs", "securityaffairs.com", "media report", editorial=True
    ),
    "databreaches": SourceProfile(
        "databreaches", "DataBreaches.net", "databreaches.net", "data-breach specialist report", editorial=True
    ),
    "hibp": SourceProfile(
        "hibp", "Have I Been Pwned", "haveibeenpwned.com", "structured data-breach catalogue record"
    ),
    "californiaag": SourceProfile(
        "californiaag", "California AG", "oag.ca.gov", "regulatory data-breach notice"
    ),
    "hhsocr": SourceProfile(
        "hhsocr", "HHS OCR", "ocrportal.hhs.gov", "regulatory healthcare breach record"
    ),
    "secedgar": SourceProfile(
        "secedgar", "SEC EDGAR Item 1.05", "sec.gov", "primary cybersecurity disclosure"
    ),
    "ddosia": SourceProfile(
        "ddosia", "DDoSia Monitor", "ddosia.rfeed.it", "DDoS target observation"
    ),
}

ALIASES = {
    "ransomwarelive": "ransomware.live",
    "ransomware.live": "ransomware.live",
    "ransomfeed": "ransomfeed",
    "ransomlook": "ransomlook",
    "ransomnews": "ransomnews",
    "ransomtracker": "ransomnews",
    "vulone": "vulone",
    "threatvectr": "threatvectr",
    "bleepingcomputer": "bleepingcomputer",
    "cybernews": "cybernews",
    "securityaffairs": "securityaffairs",
    "security affairs": "securityaffairs",
    "databreaches": "databreaches",
    "databreaches.net": "databreaches",
    "hibp": "hibp",
    "have i been pwned": "hibp",
    "california ag": "californiaag",
    "hhs ocr": "hhsocr",
    "sec": "secedgar",
    "sec edgar": "secedgar",
    "sec edgar item 1.05": "secedgar",
    "ddosia": "ddosia",
    "ddosia monitor": "ddosia",
}


def resolve_source(source: str) -> SourceProfile:
    key = ALIASES.get(" ".join(source.casefold().split()))
    if not key:
        raise ValueError("unsupported source")
    return PROFILES[key]


def _clean(value: str | None, label: str) -> str:
    cleaned = " ".join((value or "").split())
    if not cleaned:
        raise ValueError(f"{label} is required")
    return cleaned


BREACH_PROFILE_KEYS = {"databreaches", "hibp", "californiaag", "hhsocr", "secedgar"}

def _topic(profile: SourceProfile) -> str:
    if profile.key == "ddosia":
        return "DDoS"
    if profile.key in BREACH_PROFILE_KEYS:
        return "data breach"
    return "ransomware"


def _site(profile: SourceProfile) -> str:
    return f"site:{profile.domain}"


def build_queries(
    source: str,
    kind: str,
    *,
    victim: str | None = None,
    group: str | None = None,
    country: str | None = None,
    sector: str | None = None,
    host: str | None = None,
    date: str | None = None,
    month: str | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    profile = resolve_source(source)
    kind = kind.strip().casefold()
    site = _site(profile)
    topic = _topic(profile)
    queries: list[str] = []

    if kind == "victim":
        value = _clean(victim, "victim")
        queries = [
            f'{site} "{value}"',
            f'{site} "{value}" {topic}',
        ]
    elif kind == "group":
        value = _clean(group, "group")
        queries = [
            f'{site} "{value}" {topic}',
            f'{site} "{value}" {("targets" if profile.key == "ddosia" else "breach" if profile.key in BREACH_PROFILE_KEYS else "victims")}',
        ]
    elif kind == "country":
        value = _clean(country, "country")
        queries = [
            f'{site} "{value}" {topic}',
            f'{site} "{value}" {("targets" if profile.key == "ddosia" else "breach" if profile.key in BREACH_PROFILE_KEYS else "victims")}',
        ]
    elif kind == "sector":
        value = _clean(sector, "sector")
        queries = [
            f'{site} "{value}" {topic}',
            f'{site} "{value}" {("targets" if profile.key == "ddosia" else "breach" if profile.key in BREACH_PROFILE_KEYS else "victims")}',
        ]
    elif kind == "date":
        value = _clean(date, "date")
        queries = [
            f'{site} "{value}"',
            f'{site} "{value}" {topic}',
        ]
    elif kind == "month":
        value = _clean(month, "month")
        queries = [
            f'{site} "{value}" {topic}',
            f'{site} "{value}" {("targets" if profile.key == "ddosia" else "breach" if profile.key in BREACH_PROFILE_KEYS else "victims")}',
        ]
    elif kind == "host":
        value = _clean(host, "host")
        queries = [
            f'{site} "{value}"',
            f'"{value}" {profile.name}',
        ]
    elif kind == "recent":
        queries = [
            f'{site} {topic} recent',
            f'{site} {topic} latest',
        ]
    elif kind == "text":
        value = _clean(text, "text")
        queries = [
            f'{site} "{value}"',
            f'"{value}" "{profile.name}"',
        ]
    else:
        raise ValueError("unsupported kind")

    # Source-specific refinements.
    if profile.key == "ransomware.live":
        queries.append(f'{site} "ransomware.live" {queries[0].split(" ", 1)[-1]}')
    elif profile.key == "ransomfeed":
        queries.append(f'{site} "Ransomfeed" {queries[0].split(" ", 1)[-1]}')
    elif profile.key == "ransomlook":
        queries.append(f'{site} "RansomLook" {queries[0].split(" ", 1)[-1]}')
    elif profile.key == "ransomnews":
        queries.append(f'{site} "Ransomtracker" {queries[0].split(" ", 1)[-1]}')
    elif profile.key == "ddosia":
        if kind == "recent":
            queries = [
                f'{site}/index.php "DDoSia" "Last 24 hours"',
                f'{site} "DDoSia Target Monitoring" "Updated"',
                '"DDoSia" NoName057 recent targets',
            ]
        elif kind in {"host", "victim", "text"}:
            queries = [
                q.replace("ransomware", "DDoS").replace("victims", "targets")
                for q in queries
            ]
        elif kind in {"country", "date", "month"}:
            queries = [
                q.replace("ransomware", "DDoS").replace("victims", "targets")
                for q in queries
            ]

    return {
        "source": profile.name,
        "domain": profile.domain,
        "kind": kind,
        "queries": list(dict.fromkeys(queries)),
        "channel": "Search index",
        "semantic_unit": profile.semantic_unit,
        "policy": {
            "freshness_required": True,
            "source_attribution_required": True,
            "direct_transport_state_preserved": True,
            "complete_period_not_assumed": True,
            "editorial_source": profile.editorial,
            "aggregate_only": profile.aggregate_only,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("kind", choices=[
        "victim", "group", "country", "sector", "date", "month", "host", "recent", "text"
    ])
    parser.add_argument("--victim")
    parser.add_argument("--group")
    parser.add_argument("--country")
    parser.add_argument("--sector")
    parser.add_argument("--host")
    parser.add_argument("--date")
    parser.add_argument("--month")
    parser.add_argument("--text")
    args = parser.parse_args()

    try:
        result = build_queries(
            args.source,
            args.kind,
            victim=args.victim,
            group=args.group,
            country=args.country,
            sector=args.sector,
            host=args.host,
            date=args.date,
            month=args.month,
            text=args.text,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
