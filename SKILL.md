---
name: ransomware-tracker
description: Unified cyber threat intelligence for ransomware, DDoS, data-breach intelligence, historical trends, and cross-threat correlation. Routes Tracker/Trend requests across ransomware/DDoS/breach scopes, applies maximum-effort live-source and search-index fallback, preserves one canonical event/state contract, and correlates threats with evidence/identity gates. Use for victim/group/domain lookup, trend analysis, DDoS target monitoring, breach verification, and cross-threat correlation.
---

**Author: Enrico Frumento**

**Version: v7**

# Purpose

Check whether a named organization, vendor, municipality, domain, or ransomware group appears in recent or requested-period ransomware/breach data using live API sources first and verified public OSINT as fallback.

# Canonical cross-layer contracts

Read `references/unified-data-model.md` before combining live, historical, breach, DDoS, or correlation records.

Use `scripts/contracts.py` as the deterministic source of truth for source states and canonical event fields. Normalize claim-like live records through `scripts/normalize_records.py`; downstream filtering and correlation must use canonical `date`, `date_semantics`, `domain`, `data_type`, and `provenance`.

Do not create parallel downstream schemas with `published_at`/`record_type`. Accept legacy/source-specific field names only at adapter boundaries.

Only `scripts/coverage_gate.py` may authorize maximum-effort completion. A positive result from any individual source never permits early exit.

# Unified intent routing

At the start of every request, classify intent as `TRACKER` or `TREND`. Use `scripts/intent_router.py` when deterministic routing is useful, then apply semantic judgment for ambiguous wording.

- Route to **TRACKER** for named victim/company/domain lookup, named-group profile/current claims, recent victims, or record-level verification. Read `references/tracker-mode.md`.
- Route to **TREND** for time series, rankings, comparison, country/sector distributions, historical periods, wallet/ransom analysis, EuRepoC/legal analysis, or aggregated statistics. Read `references/trend-mode.md`.
- If a request contains both, choose TREND when aggregation/comparison is the primary deliverable and use Tracker behavior for the record-level subtask.
- User-explicit mode or source constraints override automatic routing.

Both modes share the same live-source scripts, fallback/replacement rules, status evidence gate, provenance rules, rate-limit behavior, and maximum-effort execution. Do not duplicate or reintroduce legacy GPT Actions.

## Global runtime-resilience rule

For configured live sources, do not equate direct transport failure with source unavailability. Read `references/runtime-search-index-fallback.md`.

After Python/API/feed, exact Web→API, and verified public-page/feed attempts, use host-native **web search/search-index recovery** before assigning a terminal unavailable state when search remains available.

Use `scripts/search_index_fallback.py` to build source-specific queries for ransomware.live, Ransomfeed, RansomLook, Ransomnews/Ransomtracker, VULONE, ThreatVectr, DataBreaches.net, Have I Been Pwned, California AG, HHS OCR, SEC EDGAR, BleepingComputer, Cybernews, and Security Affairs. DDoSia may also use its dedicated search-index helper.

When indexed source content is useful, report channel `Search index`, preserve failed direct transports in the note, and keep freshness/completeness/semantic-unit checks separate. Search-index evidence is not automatically complete, independent, or functionally equivalent.

## DDoSia runtime-resilience rule

For DDoSia requests, do not terminate coverage after Python/API and direct web fetch failures. Read `references/ddosia-runtime-fallback.md`.

After direct API, Web→API, and public-page fetch attempts, use host-native **web search/search-index recovery** before declaring DDoSia unavailable. Search engines may expose current indexed DDoSia dashboard/search content even when the runtime cannot directly fetch the domain.

Use `scripts/ddosia_search_fallback.py` to construct stable queries when useful.

When indexed DDoSia content is usable, report the source with channel `Search index` and preserve the direct transport failure in the note. Do not claim complete monthly/date coverage unless the retrieved evidence actually supports completeness.

# Breach intelligence layer

For data-breach lookup, trend analysis, or ransomware ↔ data-breach correlation, read `references/breach-intelligence.md` and use `scripts/breach_sources.py`.

Dedicated breach sources:
- DataBreaches.net — specialist editorial OSINT;
- Have I Been Pwned — structured breach catalogue;
- California AG — regulatory breach notices;
- HHS OCR — regulatory healthcare breach records;
- SEC EDGAR Item 1.05 — primary cybersecurity disclosures.

Keep BleepingComputer, Security Affairs, and Cybernews as general OSINT corroborators. Preserve incident/breach dates separately from publication, filing, reported, submission, and catalogue-added dates.

# Threat-actor identity resolution

Before merging actor/group records across sources or threat families, read `references/actor-identity.md` and use `scripts/actor_identity.py` when deterministic alias/collision handling is useful.

Apply these invariants:
- exact or normalized name equality does not prove actor identity;
- merge different labels only through a verified alias set;
- preserve `ENTITY_COLLISION` when the same-looking label identifies different actors;
- preserve original source labels after canonicalization;
- do not let vendor naming alone redefine operation type.

Use the discussed NoName homonym case and Luna Moth/Silent Ransom Group multi-alias case only as illustrative reasoning examples. Do not hard-code them as production identity rules. Re-derive actor mappings from current evidence and apply the same generic collision/verified-alias logic to any actor.

# Cross-correlation layer

When the user asks whether different cyber-event families are connected, overlapping, correlated, or occur around the same victims/periods, activate the isolated cross-correlation module in addition to the normal Tracker/Trend routing.

Read `references/cross-correlation.md` and use `scripts/cross_correlation.py`.

Supported profiles:
- ransomware ↔ DDoS — default tolerance ±14 days;
- ransomware ↔ data breach — ±30 days;
- ransomware ↔ credential leak — ±30 days;
- ransomware ↔ exploit activity — ±21 days;
- DDoS ↔ hacktivism campaign — ±14 days;
- ransomware ↔ vulnerability exploitation — ±30 days.

Treat matches as temporal co-occurrence/correlated exposure unless explicit evidence establishes causality. Actor-equality confidence boost is valid only for matching verified `canonical_actor_id` values; raw actor/group string equality is insufficient. Apply profile-specific evidence gates and classify results as `DIRECT`, `CONTEXTUAL`, or `REJECTED`; only `DIRECT` contributes to strict incident-level counts. Distinguish `same_incident`, `temporal_cooccurrence`, and `campaign_context`, preserve date semantics, and keep ransomware encryption distinct from data extortion. Keep this module isolated so future cross profiles can be added without modifying the core Tracker/Trend workflows.

# Historical knowledge base

The skill bundles verified historical data under `assets/historical/`:

- `ransom.json` — historical incident/claim-oriented records;
- `ransom2.json` — structured victim/group/country/sector records;
- `recent.json` — claim-oriented records with attack/discovery metadata;
- `wallets.json` — ransomware-linked wallet observations and USD transaction/balance fields;
- `eurepoc_global_dataset_1_3.csv` — EuRepoC cyber-incident/legal/attribution dataset;
- `ransomware_repository.csv` — historical ransomware incident repository.

Use `scripts/historical_query.py` for deterministic local filtering and aggregation. Treat the local datasets as historical evidence with their own coverage boundary, not as automatically current.

For live/current periods, enrich and extend them with the shared live-source engine. Never use the legacy Action definitions from the source KB; they are intentionally excluded from the packaged skill.

## Conditional sector enrichment

When the requested result materially requires sector information and a victim record has no sector, use targeted public-web enrichment rather than guessing.

Read `references/sector-enrichment.md` and use `scripts/sector_enrichment.py` to prepare queries and validate candidate evidence when deterministic validation is useful.

- Trigger enrichment only for sector-dependent requests.
- Use the victim's exact name plus available disambiguators.
- For a natural person, require identity disambiguation beyond name alone.
- Prefer official/employer/registry/government evidence.
- Accept reputable secondary sources only when identity and sector are explicit.
- Never infer sector from weak context, article adjacency, surname, ransomware group, or domain wording alone.
- Preserve the original source record and mark the sector as web-enriched with provenance/confidence.
- If evidence is ambiguous or conflicting, keep sector unknown.

This web enrichment uses host-native web search/fetch and must not reintroduce legacy GPT Actions.

# Analytical flexibility

Support flexible questions by composing generic filters and aggregations instead of hard-coding query-specific flows:

- filters: victim, group, country, sector, date range, source;
- grouping: month, quarter, year, group, country, sector;
- metrics: record counts, distinct groups/victims, wallet USD fields, legal/attribution incident counts where semantically valid;
- outputs: record tables, comparative tables, rankings, time series, concise analytical narrative, charts when supported, and JSON export when requested.

Always label the semantic unit being counted. Do not call leak-site claims “confirmed attacks” unless independently confirmed.

# Runtime references

For every normal lookup, read:

- `references/operating-rules.md`
- `references/source-map.md`

Read `references/python-discipline.md` only when maintaining, reviewing, testing, or changing Python code.

# Execution workflow

For every operational lookup or trend request, consult **all sources relevant to the selected threat-family scope in the current run** and use **maximum-effort execution**, not best-effort execution.

1. Interpret the request: victim/vendor lookup, group lookup, country/date query, trend/statistics query, or explicit source-specific query.
2. Query all API sources:
   - `scripts/ransomware_live.py`
   - `scripts/ransomlook.py`
   - `scripts/ransomfeed.py`
3. Query all OSINT sources:
   - `scripts/bleepingcomputer.py`
   - `scripts/cybernews.py`
   - `scripts/security_affairs.py`
4. For every source, exhaust all safe and supported retrieval paths before assigning a terminal non-success state:
   - source-specific Python helper;
   - bounded retry when the failure is transient and retry is allowed;
   - canonical exact endpoint through another available transport when supported;
   - verified public fallback page/feed for that source when available.
5. Respect explicit upstream rate limits. `429` is not a reason to abandon the source; wait according to `Retry-After` or the configured source policy, then retry within the bounded maximum-effort policy.
6. For each source, record a current-run ledger entry containing attempted flag, state, channel, evidence, and which retrieval paths were exhausted.
7. Preserve each helper's explicit state; never convert `BLOCKED`, `RATE_LIMITED`, `INVALID_RESPONSE`, or `UNAVAILABLE` into a negative match.
8. Normalize successful records with `scripts/normalize_records.py`.
9. Apply keyword/country/date filters and deduplication with `scripts/filter_records.py`.
10. Merge/corroborate findings across all sources while preserving provenance.
11. Validate relevant-scope coverage with `scripts/coverage_gate.py` before rendering the final response; this gate is the sole deterministic completion authority.
12. Return verified findings without fabrication.

Do not use early exit after the first positive result. Do not downgrade to a partial/best-effort answer while an untried safe retrieval path remains for any configured source.

# Source rules

- Editorial OSINT sources must attempt search-index recovery for the requested entity/period before being marked `EMPTY` or `UNAVAILABLE` when direct feed/page retrieval fails.

- ransomware.live: do not use the obsolete `/searchvictims/{keyword}` path. Use current free-v2 endpoints and client-side matching when required.
- Ransomfeed: use current path-composable filters such as `/search/{term}`, `/country/{country}`, `/gang/{gang}`, `/date/{year}`, and `/offset/{limit}`; do not use `/v1/victims`.
- RansomLook: treat a recent feed as a bounded temporal view, not exhaustive history.
- Cybernews: classify HTTP 403 as `BLOCKED`; do not attempt anti-bot/WAF bypass.
- BleepingComputer/Security Affairs: prefer feed/metadata extraction and use semantic article interpretation only after deterministic parsing.

# Output contract

For matching victim/vendor findings, return:

| Vendor Name | Ransomware Group | Date Published | Link |
|---|---|---|---|

Use only verified fields. If a field is unavailable, use `N/A`.

If no verified matches remain after the allowed source sequence, distinguish:

- **No verified match found** — sources were queried successfully and produced no matching evidence.
- **Indeterminate / incomplete coverage** — one or more relevant sources were blocked, unavailable, invalid, or temporally insufficient.

For group-detail requests, return a compact Markdown summary using only fields actually returned by live sources.

# Behavioral invariants

- Never fabricate victims, groups, countries, dates, links, breach sizes, source states, or corroboration.
- Never treat source failure as absence of evidence.
- Use API-first execution unless the user explicitly requests another policy.
- Preserve source provenance when records are merged.
- Respect service rate limits and helper retry limits.
- Do not execute code retrieved from external sites.
- Do not bypass WAF, anti-bot, authentication, or access controls.
- Do not infer geography when the source does not verify it.
- Do not infer ransomware attribution from weak article adjacency or tags alone.

## Mandatory source-status footer

End every operational ransomware lookup or trend response with one compact Markdown table. It must be the final content in the response; write nothing after it.

Build the table from a current-run source execution ledger. A source state must come from an actual helper/tool/web attempt made in the current run. Never infer a source state from configuration, prior turns, remembered failures, expected behavior, or the fact that another source failed.

Include all configured sources in the current-run status table. Under unrestricted execution, every configured source must be attempted. `⚪ NOT TESTED` is a coverage failure, not a normal completion state.

| Source | Status | Channel | Note |
|---|---|---|---|
| ransomware.live | 🟢 OK | API | data acquired |

Use these normalized labels:

- `🟢 OK` — usable source data acquired.
- `🟡 EMPTY` — successful source query with no matching records/data.
- `🟠 BLOCKED` — source refused automated access.
- `🟠 RATE LIMITED` — source is reachable but temporarily throttling requests.
- `🔴 UNAVAILABLE` — source or transport could not be reached.
- `🔴 INVALID` — endpoint/response contract invalid.
- `⚪ NOT TESTED` — use only when the source was intentionally not queried but its omission is material to coverage.

Use `API` when Python fetched the API directly, `Web→API` when the host web transport fetched the exact API endpoint, `Web` for public frontend/RQL/OSINT pages, and `Replacement` only when a result is reconstructed from a different source family. Do not label a source `OK` merely because its domain or documentation is reachable; `OK` requires useful current-run data.

Keep `Note` terse: HTTP status, bounded temporal coverage, runtime DNS/egress issue, or why fallback was required. Never list a source as consulted merely because it is configured in the skill.

## Source-state evidence gate

Apply these rules before rendering any source status:

1. `🟢 OK` requires a current-run successful response with usable data/content.
2. `🟡 EMPTY` requires a current-run successful request whose returned data is valid but contains no matching records.
3. `🟠 BLOCKED` requires a current-run response that explicitly indicates access refusal, such as HTTP 403.
4. `🟠 RATE LIMITED` requires a current-run rate-limit signal, normally HTTP 429.
5. `🔴 UNAVAILABLE` requires a current-run attempted request plus concrete transport/source failure evidence such as DNS failure, TLS/socket error, timeout, egress denial, or upstream 5xx. Never assign `UNAVAILABLE` to a source that was not called.
6. `🔴 INVALID` requires a current-run response proving an invalid endpoint/contract or malformed incompatible response.
7. `⚪ NOT TESTED` means no request was attempted in the current run. Under unrestricted execution, this is a coverage failure and the run must continue if any safe supported retrieval path remains.
8. If evidence is insufficient to justify a failure state, do not invent one. Either omit the source or mark it `NOT TESTED` only if no request was attempted.

The final row note must be traceable to current-run evidence: HTTP status, exception class/message, successful empty response, temporal limitation, or an explicit reason the source was intentionally skipped.

Before writing the footer, reconcile every row against the current-run execution ledger. If no ledger entry exists for a source, that source cannot be `OK`, `EMPTY`, `BLOCKED`, `RATE LIMITED`, `UNAVAILABLE`, or `INVALID`.

## Transport diagnostic rule

A successful raw Python GET to a source proves that local DNS, TLS, and direct HTTPS transport are available in that environment. If the source-specific helper fails while an equivalent raw GET succeeds, diagnose the helper request construction or request fingerprint before declaring the source unavailable.

For ransomware.live, use the shared conservative headers and the canonical API URL. Preserve Web→API fallback for runtime portability, but prefer direct Python API retrieval when it succeeds.

## Source diagnostics

When a source helper disagrees with a raw browser/curl/Python GET, diagnose the deployed runtime before changing endpoint semantics. Run `scripts/diagnose_source.py` for the exact source operation. Prefer per-content request profiles (`api`, `rss`, `html`) over one global Accept header.

A successful raw GET plus a failing helper indicates helper construction/fingerprint behavior, not source unavailability.

## Source reachability policy

Treat source availability and transport availability as separate facts.

For every configured source:

1. Try the source-specific Python helper when direct network access exists.
2. If Python fails at DNS/egress/TLS or returns a transport-anomalous result, generate the exact URL with `scripts/request_manifest.py`.
3. If direct Python transport fails because of DNS, egress, TLS, or another runtime transport limitation, try the exact API URL through the host web transport when that capability is available.
4. If the exact API/feed endpoint cannot be opened but a public fallback route exists, use that page as OSINT fallback and mark the channel `Web`, not `Web→API`.
5. Only mark a source `INVALID` when the endpoint or response contract is confirmed invalid, not when one transport channel fails.
6. Never infer that a source itself is down from a runtime-wide DNS or egress failure.
7. Treat transport capability as runtime-local and ephemeral; do not permanently disable a transport because it failed in a previous environment or session.

For ransomware.live month queries, keep the canonical manifest URL available so the same request can be retried through another transport without changing source semantics.

## Rate-limit handling

Classify HTTP 429 as `RATE_LIMITED`. Respect a numeric `Retry-After` header when present. For ransomware.live, if the response states a one-request-per-minute limit and no usable header is present, wait 65 seconds before a single retry. Never run parallel duplicate requests against the same ransomware.live endpoint. Cache and reuse successful results within the current execution.

A rate-limited source is reachable. Do not report it as unavailable. If another configured source or a web fallback can satisfy the request while the rate-limit window is active, continue with that coverage and expose the rate-limited source in the final status table.

## Anti-overfitting transport policy

Keep transport rules generic and evidence-based.

- Separate source validity from runtime transport availability.
- Do not permanently blacklist a source or transport because one sandbox, session, or client failed.
- Do not encode one user query, one country, one sector, or one date range as a special path unless the upstream API explicitly defines it.
- Prefer capability checks at runtime over static per-environment assumptions.
- Preserve the same canonical source request while switching transport.
- Use source-specific behavior only for documented upstream semantics, such as endpoint shape, content type, or rate limiting.
- When evidence is incomplete, report incomplete coverage instead of creating a special-case heuristic.

## Runtime-wide DNS and egress diagnosis

Treat repeated DNS failures across independent source domains as possible runtime-wide transport failure, not as independent source outages.

When at least two unrelated configured domains fail with the same DNS/egress class in the current run:

1. avoid redundant retries after one per-source attempt establishes the same runtime-wide resolver error, but still attempt every configured source at least once;
2. run `scripts/network_diagnostics.py` when deterministic diagnostics are available;
3. keep system DNS as the operational resolver;
4. use a public resolver such as `8.8.8.8` only as an optional diagnostic probe;
5. never substitute public-DNS results or hard-coded IPs into source HTTPS requests;
6. if system DNS fails and direct public DNS over both UDP/TCP 53 also fails, classify the condition as a runtime-wide DNS/egress restriction;
7. switch to another supported transport, preserving the same canonical source request;
8. never convert the runtime-wide condition into `UNAVAILABLE` for sources that were not individually attempted.

A public resolver is diagnostic evidence only. It is not an operational bypass for sandbox network policy.

## Maximum-effort execution policy

Use maximum-effort execution for every configured source.

A source is complete only when one of these conditions is true:

- usable data was obtained;
- the source returned a valid empty result;
- a definitive source-side block/invalid response was observed and no alternate safe transport can change the outcome;
- a rate limit was encountered and all policy-compliant retry opportunities for the current run were exhausted;
- every safe supported retrieval path for that source was attempted and failed with current-run evidence.

Never stop at the first transport failure. Never treat one DNS/TLS/socket failure as terminal if another supported transport remains. Never stop because another source already produced enough data.

Maximum effort remains bounded and policy-compliant:
- respect rate limits and explicit `Retry-After`;
- do not bypass authentication, WAF, anti-bot, or access controls;
- do not use unsafe IP substitution or resolver bypass;
- do not loop indefinitely;
- do not fabricate success when all paths fail.

The final answer is allowed to contain incomplete source coverage only after all safe supported retrieval paths have been exhausted and that exhaustion is recorded in the current-run ledger.

## All-source consultation policy

Configured sources/surfaces:
- ransomware.live
- Ransomfeed API
- Ransomfeed Web/RQL
- RansomLook
- Ransomnews/Ransomtracker
- VULONE
- ThreatVectr
- BleepingComputer
- Cybernews
- Security Affairs

For every unrestricted operational lookup or trend request, attempt every configured source/surface in the current run with maximum effort. Positive findings from one source never suppress consultation of another source. Replacement sources are still consulted even when the primary succeeds so freshness, lineage, and cross-source divergence can be assessed.

## Functional replacement architecture

Optimize every primary-source failure as:

`source failure -> transport fallback -> functional replacement -> corroboration -> provenance disclosure`

Do not jump directly from a primary transport failure to incomplete coverage while a qualified replacement path remains.

Track five dimensions independently for every source/surface:

1. **Reachability** — whether the current runtime acquired content.
2. **Freshness** — whether the acquired content covers the requested period.
3. **Functional equivalence** — whether the source supplies the requested data type.
4. **Independence / lineage** — whether corroboration is epistemically independent or likely derived/overlapping.
5. **Data type** — distinguish claim/victim record, group profile, confirmed incident, and aggregate statistic.

Use `scripts/replacement_policy.py` to select/qualify replacement paths when deterministic execution is available.

### ransomware.live maximum-effort ladder

Attempt, in order when applicable:

1. canonical Python/API helper;
2. exact canonical endpoint through host Web→API transport;
3. documented API Pro surface when accessible without violating access controls;
4. public ransomware.live web surface when it provides the required data;
5. Ransomnews/Ransomtracker;
6. RansomLook;
7. VULONE, only if freshness is compatible with the requested period;
8. ThreatVectr only for aggregate statistics/trends/rankings.

Never use hard-coded IPs, DNS substitution, `curl --resolve`, WAF/CDN bypass, or any routing alteration.

### Ransomfeed maximum-effort ladder

Attempt, in order when applicable:

1. direct API helper;
2. exact API endpoint through host Web→API transport;
3. Ransomfeed public Web surface;
4. Ransomfeed RQL structured search;
5. RansomLook;
6. Ransomnews/Ransomtracker;
7. VULONE, subject to freshness qualification.

Treat Ransomfeed Web/RQL as the same source family for lineage but as a distinct operational surface with channel `Web`.

### Replacement qualification gate

Before describing a source as a functional replacement, require current-run evidence for:

1. reachability;
2. useful content actually acquired;
3. freshness compatible with the query;
4. required victim/group/date fields when victim-level use is requested;
5. sufficient history for the requested period;
6. reproducible lookup/filter behavior;
7. coherence on multiple sample groups/records when qualification depends on cross-source comparison;
8. declarable provenance/lineage;
9. absence of obsolete-only dependency;
10. no access-control bypass.

HTTP 200 or documentation reachability alone is never enough.

### Source-specific replacement roles

- **RansomLook** — strong current claims/group/history source; may act as primary claims source when ransomware.live is unavailable.
- **Ransomnews/Ransomtracker** — structured secondary replacement with group profiles, claim/victim records, dates, and aggregates. Do not count it automatically as independent corroboration from RansomLook; disclose probable overlap when records/counts align closely.
- **Ransomfeed Web/RQL** — structured Web replacement for the Ransomfeed API with reproducible victim/gang/country/date/sector filters and statistics where exposed. Same-family lineage; channel `Web`.
- **VULONE** — third-line victim/group/date/geography corroboration. Require freshness compatibility. Treat independence as partial because its public methodology states cross-checking with ransomware.live/RansomLook.
- **ThreatVectr** — aggregate-only sanity check for trends/rankings/monthly statistics. Do not use as victim-level replacement unless a directly exposed victim record exists for the needed claim.
- **RansomWatch GitHub** — do not use as a current fallback when its dataset is stale for the requested period. Reachability never overrides freshness.

### Independence and lineage

Never equate two reachable surfaces with two independent datasets.

If two trackers expose near-identical counts, dates, and records, report them as separate operational surfaces but mark independence as uncertain/overlapping. Do not increase confidence merely by double-counting likely shared lineage.

For aggregate statistics, do not blindly sum counts from different trackers. Prefer one internally coherent series; otherwise present cross-source values separately and disclose divergence or a range.

## Replacement disclosure

When replacement sources materially reconstruct a result, include one concise note before the final source-status table:

“Primary source unavailable in current runtime; result reconstructed from verified replacement sources X and Y.”

Do not retroactively change the primary source status. Keep the primary failure state supported by current-run evidence and list each replacement source separately with its actual channel and role.

## Legacy Actions are prohibited

Do not invoke or recreate the old GPT Action/OpenAPI integration layer. Use the bundled Python helpers and host-native web/browser/fetch transport defined by this skill. The historical KB data is retained; legacy Action schemas are not part of the runtime.
