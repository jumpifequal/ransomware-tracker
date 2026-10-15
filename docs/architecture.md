# Architecture

This page describes how the skill works. It follows `SKILL.md`, which stays the source of truth.

![End-to-end pipeline](assets/pipeline.svg)

## Two modes, one engine

At the start of every request the skill chooses a mode.

| Mode | Use for | Reads |
|---|---|---|
| `TRACKER` | A named victim, company, domain or group; recent victims; record-level checks | `references/tracker-mode.md` |
| `TREND` | Time series, rankings, comparisons, country or sector distributions, wallet and ransom analysis, legal analysis | `references/trend-mode.md` |

`scripts/intent_router.py` gives an advisory choice. If the user states a mode or a source limit, that choice wins. If a request needs both, the skill chooses `TREND` when comparison is the main result and uses Tracker behaviour for record-level steps.

Both modes share the same live-source scripts, fallback rules, status gate and provenance rules.

## Execution workflow

1. Interpret the request.
2. Query all API sources: `ransomware_live.py`, `ransomlook.py`, `ransomfeed.py`.
3. Query all OSINT sources: `bleepingcomputer.py`, `cybernews.py`, `security_affairs.py`.
4. For every source, try all safe retrieval paths before a terminal state: the helper, a bounded retry, the same endpoint through another transport, a verified public page or feed, and search-index recovery.
5. Respect rate limits. HTTP 429 is not a reason to drop a source.
6. Write a current-run ledger entry for each source.
7. Keep each helper's state. `BLOCKED`, `RATE_LIMITED`, `INVALID_RESPONSE` and `UNAVAILABLE` never become a negative match.
8. Normalize records with `normalize_records.py`.
9. Filter and de-duplicate with `filter_records.py`.
10. Merge and corroborate, keeping provenance.
11. Check coverage with `coverage_gate.py`. This gate alone can authorize completion.
12. Return verified findings and the source-status table.

## Extra layers

| Layer | Purpose | Main files |
|---|---|---|
| Breach intelligence | Breach lookup, trends and ransomware ↔ breach correlation | `references/breach-intelligence.md`, `scripts/breach_sources.py` |
| Actor identity | Merge actor labels only through verified aliases; keep same-name collisions apart | `references/actor-identity.md`, `scripts/actor_identity.py` |
| Cross-correlation | Profile-driven correlation with evidence gates (`DIRECT`, `CONTEXTUAL`, `REJECTED`) | `references/cross-correlation.md`, `scripts/cross_correlation.py` |
| Historical knowledge base | Local datasets for claims, wallets, EuRepoC incidents and a ransomware repository | `assets/historical/`, `scripts/historical_query.py` |
| Sector enrichment | Targeted web enrichment when a sector is required and missing | `references/sector-enrichment.md`, `scripts/sector_enrichment.py` |
| DDoS | DDoSia Monitor lookups and statistics, kept apart from ransomware victims | `scripts/ddosia.py`, `references/ddosia-runtime-fallback.md` |

## Status gate

The skill ends every operational answer with one table. A source state needs evidence from the current run: an actual helper, tool or web attempt. The table is the last content of the answer.

## Functional replacement

When a primary source fails, the skill follows this order: `source failure -> transport fallback -> functional replacement -> corroboration -> provenance disclosure`. It tracks reachability, freshness, functional equivalence, independence and data type separately for each source. `scripts/replacement_policy.py` helps to select and qualify replacements.
