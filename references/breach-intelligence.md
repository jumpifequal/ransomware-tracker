# Breach intelligence layer

Use this layer for data-breach discovery, confirmation, regulatory evidence, and ransomware ↔ data-breach correlation.

## Source roles

Treat source quality as an evidence role rather than raw source count:

1. `PRIMARY_DISCLOSURE` — registrant/company primary disclosure such as SEC EDGAR Item 1.05.
2. `REGULATORY` — California Attorney General breach notices and HHS OCR breach records.
3. `STRUCTURED_CATALOGUE` — Have I Been Pwned breach catalogue.
4. `SPECIALIST_OSINT` — DataBreaches.net.
5. `GENERAL_OSINT` — BleepingComputer, Security Affairs, Cybernews.

Repeated articles derived from one underlying notice are not independent corroboration.

## Dedicated retrieval

Use `scripts/breach_sources.py` for direct public retrieval:

- DataBreaches.net: RSS/site search.
- Have I Been Pwned: public breach catalogue endpoints.
- California AG: breach list/search.
- HHS OCR: public breach portal.
- SEC EDGAR: public filing search surface.

If direct transport fails, continue through exact native-web transport, public page/data surface, then source-attributed search-index recovery where available.

## Date semantics

Keep distinct:
- `incident_date`
- `breach_date`
- `discovery_date`
- `disclosure_date`
- `publication_date`
- `reported_date`
- `submission_date`
- `filing_date`
- `catalog_added_date`

For ransomware ↔ data-breach correlation, prefer actual incident/breach dates. Use disclosure/publication/catalog dates only when the event date is unavailable and downgrade confidence.

## Coverage

For `BREACH` scope, consult all configured dedicated breach sources plus the general OSINT corroborators. For `RANSOMWARE_BREACH`, combine ransomware and breach source scopes without duplicating shared editorial sources.

Do not finalize a no-match or a cross-threat correlation while the coverage gate reports an unattempted material source or an untried safe retrieval path.
