"""
Purpose: route ransomware requests to TRACKER or TREND analysis mode.
When used: at the start of every user request handled by the unified ransomware skill.
Why it exists: keeps entity/claim lookups separate from aggregation, historical, financial, legal, and comparative analysis while sharing the same live-source scripts.
Inputs/parameters: free-text user request.
Outputs: JSON with selected mode, scores, matched signals, and a concise routing reason.
High-level behavior: applies deterministic intent signals; aggregation/historical/financial/legal requests prefer TREND, while entity/current-record lookups prefer TRACKER.
Failure semantics: ambiguous requests default to TRACKER only when no trend signal exists; the result is advisory and may be overridden by explicit user intent.
"""
from __future__ import annotations

import argparse
import json
import re

TREND_TERMS = (
    "trend", "andamento", "serie temporale", "mensile", "mensili", "trimestrale",
    "trimestre", "annuale", "per anno", "per mese", "ranking", "top ",
    "statistica", "statistiche", "confronta", "comparazione", "comparativo",
    "settore", "settori", "distribuzione", "percentuale", "quota", "evoluzione",
    "storico", "storica", "dal ", "fino al", "tra il", "periodo", "quanti",
    "numero di vittime", "riscatto", "riscatti", "wallet", "pagamenti",
    "eurepoc", "legale", "geopolit", "media", "mediana", "somma", "totale",
)

DDOS_TERMS = (
    "ddos", "d-dos", "denial of service", "distributed denial",
    "ddosia", "noname057", "noname57", "no name 057",
    "target ddos", "bersaglio ddos", "targeted by ddos",
)

BREACH_TERMS = (
    "data breach", "data breaches", "breach", "violazione dati", "violazioni dati",
    "data leak", "credential leak", "hibp", "have i been pwned", "databreaches.net",
    "california ag", "hhs ocr", "sec 8-k", "item 1.05",
)

RANSOMWARE_TERMS = (
    "ransomware", "ransom", "leak site", "leak-site", "claim ransomware",
)

TRACKER_TERMS = (
    "cerca", "trova", "verifica", "controlla", "vittima", "azienda",
    "organizzazione", "comune", "dominio", "claim", "ultimo record",
    "ultime vittime", "recenti", "gruppo", "gang", "profilo gruppo",
    "è stata colpita", "ha colpito", "compare", "presente",
)


def route(text: str) -> dict[str, object]:
    normalized = " ".join(text.casefold().split())
    trend_hits = [term for term in TREND_TERMS if term in normalized]
    tracker_hits = [term for term in TRACKER_TERMS if term in normalized]
    ddos_hits = [term for term in DDOS_TERMS if term in normalized]
    ransomware_hits = [term for term in RANSOMWARE_TERMS if term in normalized]
    breach_hits = [term for term in BREACH_TERMS if term in normalized]

    trend_score = len(trend_hits) * 2
    tracker_score = len(tracker_hits)

    # Explicit aggregation grammar is a strong TREND signal.
    if re.search(r"\b(per|by)\s+(mese|month|anno|year|paese|country|settore|sector|gruppo|group)\b", normalized):
        trend_score += 4
        trend_hits.append("aggregation-grammar")

    # Explicit named-entity lookup grammar is a strong TRACKER signal.
    if re.search(r"\b(cerca|trova|verifica|lookup|check)\b.+", normalized):
        tracker_score += 3
        tracker_hits.append("lookup-grammar")

    mode = "TREND" if trend_score > tracker_score and trend_score > 0 else "TRACKER"
    if ddos_hits and ransomware_hits and breach_hits:
        threat_scope = "ALL"
    elif ransomware_hits and breach_hits:
        threat_scope = "RANSOMWARE_BREACH"
    elif ddos_hits and breach_hits:
        threat_scope = "DDOS_BREACH"
    elif ddos_hits and ransomware_hits:
        threat_scope = "MIXED"
    elif breach_hits:
        threat_scope = "BREACH"
    elif ddos_hits:
        threat_scope = "DDOS"
    else:
        threat_scope = "RANSOMWARE"

    return {
        "mode": mode,
        "trend_score": trend_score,
        "tracker_score": tracker_score,
        "trend_signals": trend_hits,
        "tracker_signals": tracker_hits,
        "threat_scope": threat_scope,
        "ddos_signals": ddos_hits,
        "ransomware_signals": ransomware_hits,
        "breach_signals": breach_hits,
        "reason": (
            "aggregation/historical/financial/legal intent"
            if mode == "TREND"
            else "entity/current-record lookup intent"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request")
    args = parser.parse_args()
    print(json.dumps(route(args.request), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
