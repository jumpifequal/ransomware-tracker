# Runtime tools

The helpers live in `scripts/`. They use only the Python standard library. Each helper starts with a docstring that states its purpose, when it is used and how it fails. The table below is generated from those docstrings.

Run `python scripts/<name>.py --help` to see the options of a helper, or read its docstring first.

| Script | Purpose | When used |
|---|---|---|
| `_cli_common.py` | shared deterministic CLI validation and JSON-envelope helpers. | imported by source-specific REST adapters and deterministic processing adapters. |
| `_http_common.py` | shared HTTPS transport and deterministic response normalization for REST and OSINT helpers. | imported by each source-specific helper before invoking an allow-listed public endpoint. |
| `_source_runner.py` | shared source-adapter execution wrapper. | called by source-specific REST helpers after argument parsing and request construction. |
| `actor_identity.py` | resolve threat-actor aliases conservatively from caller-supplied evidence and detect same-name collisions before cross-source merging or correlation. | before actor/group normalization, victim deduplication by actor, and cross-threat searches where aliases or homonyms could fragment or falsely merge threat entities. |
| `bleepingcomputer.py` | retrieve public OSINT content from bleepingcomputer through allow-listed HTTPS endpoints. | when API sources need public-reporting fallback or enrichment. |
| `breach_sources.py` | query public data-breach intelligence sources used by breach lookup/trend workflows and ransomware↔data-breach correlation. | whenever the selected threat scope includes BREACH or RANSOMWARE_BREACH. |
| `contracts.py` | define shared semantic contracts used across source adapters, normalization, coverage, status rendering, filtering, and correlation. | imported by deterministic helpers that need canonical event fields or source-state semantics. |
| `coverage_gate.py` | enforce exhaustive maximum-effort coverage for the threat-family scope selected by the request. | immediately before rendering unrestricted ransomware, DDoS, breach, or mixed operational responses. |
| `cross_correlation.py` | correlate heterogeneous cyber-event families using isolated, profile-driven rules with evidence gates. | for cross-threat questions such as ransomware↔DDoS, ransomware↔data breach, ransomware↔credential leak, ransomware↔exploit activity, DDoS↔hacktivism campaign, and ransomware↔vulnerability exploitation. |
| `cybernews.py` | retrieve public OSINT content from cybernews through allow-listed HTTPS endpoints. | when API sources need public-reporting fallback or enrichment. |
| `ddosia.py` | query the public DDoSia Monitor CTI API for NoName057/DDoSia target intelligence. | for DDoS target lookups, recent DDoSia target checks, date-based extraction, available-date discovery, and DDoSia trend/statistics requests. |
| `ddosia_search_fallback.py` | generate search-engine fallback queries for DDoSia Monitor when direct API and web fetch transports are blocked. | after DDoSia API/Web→API/public-page fetch attempts fail because of runtime egress, proxy, robots, TLS, DNS, or timeout restrictions. |
| `diagnose_source.py` | diagnose DNS, HTTPS reachability, request-profile behavior, and content type for a configured source. | run manually in the deployment/runtime environment when a source helper behaves differently from a raw browser or curl request. |
| `fallback_policy.py` | summarize source-envelope outcomes and recommend the next retrieval phase without authorizing early completion. | after one retrieval layer (for example direct APIs) and before continuing maximum-effort fallback/replacement coverage. |
| `filter_records.py` | deterministically filter and deduplicate canonical event records. | after normalize_records.py and before final interpretation or cross-correlation. |
| `historical_query.py` | query and aggregate the bundled historical ransomware knowledge base using a canonical schema. | in TREND mode for time-series, country/sector/group comparisons, financial summaries, EuRepoC views, and repository history; optionally in TRACKER mode for older entity lookups. |
| `intent_router.py` | route ransomware requests to TRACKER or TREND analysis mode. | at the start of every user request handled by the unified ransomware skill. |
| `network_diagnostics.py` | diagnose DNS and outbound-network failures without treating alternate DNS as an operational bypass. | only when multiple source helpers fail at DNS/egress or when transport behavior is ambiguous. |
| `normalize_records.py` | normalize heterogeneous live-source records into one canonical event schema. | after a source helper returns successful JSON and before filtering, deduplication, or correlation. |
| `ransomfeed.py` | query the current Ransomfeed public filter API. | for victim search, country/gang/year filtering, recent records, and combined filters. |
| `ransomfeed_web.py` | query Ransomfeed's public Web/RQL surface when the direct API transport is unavailable or for cross-checking. | for structured victim/group/country/date/sector lookups and reproducible RQL queries through the public frontend. |
| `ransomlook.py` | query current RansomLook API endpoints for posts, groups, leaks, and search. | for recent posts, group intelligence, leak records, and keyword search. |
| `ransomnews.py` | query the public Ransomnews Ransomtracker surface as a structured functional replacement/corroboration source. | after ransomware.live transport failure, for group/victim claim context, or during mandatory all-source consultation. |
| `ransomware_live.py` | query the current ransomware.live free v2 endpoints and provide client-side victim search. | for recent victims, month-specific victims, groups, group victims, country victims, sector victims, and recent keyword search. |
| `regression.py` | package-level regression validation for the ransomware-tracker Universal skill. | after any structural, endpoint, metadata, reference, icon, or Python change and before packaging. |
| `replacement_policy.py` | qualify functional replacement sources and select evidence-preserving fallback ladders. | after primary-source transport failure and before declaring coverage incomplete. |
| `request_manifest.py` | construct canonical public request URLs for native-web transport fallback across configured live sources. | when a Python source helper cannot reach a host and the same canonical request should be retried through host-native web transport. |
| `search_index_fallback.py` | generate source-specific search-index recovery queries when direct API, Web→API, feed, or public-page transports are blocked. | after supported direct transports for a configured live source fail because of runtime egress, proxy, robots, DNS, TLS, or timeout restrictions. |
| `sector_enrichment.py` | prepare and validate conditional web-based sector enrichment for victim records missing sector data. | only when the user request materially requires sector information and the victim name is known but the sector is absent. |
| `security_affairs.py` | retrieve public OSINT content from securityaffairs through allow-listed HTTPS endpoints. | when API sources need public-reporting fallback or enrichment. |
| `source_status.py` | validate and normalize per-source status rows from current-run evidence. | immediately before rendering the mandatory source-status footer. |
| `threatvectr.py` | query ThreatVectr public monthly ransomware reports for aggregate trend and ranking sanity checks. | for monthly/period statistics, rankings, and mandatory all-source aggregate corroboration. |
| `vulone.py` | query VULONE public ransomware group/victimology pages as a tertiary corroboration source. | during all-source consultation and as a third-line check after primary/secondary claim sources. |

## Package checks

- `tests/test_code.py` runs deterministic unit-style tests without live network access.
- `scripts/regression.py` checks package invariants, compiles every Python file, runs the tests and rejects build residue.
- `tools/validate_repo.py` checks the repository wrapper and runs both checks above.
