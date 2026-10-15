# Changelog

**Repository packaging - skill version unchanged (v7)**

- add: GitHub repository wrapper — short README in English and Italian, with worked examples and advanced use on separate documentation pages, a pipeline diagram, an illustrative dashboard, two workflow infographics (English and Italian), suggested prompts with verified expected results, and credits for the historical data; Apache-2.0 LICENSE, CONTRIBUTING, SECURITY, documentation, CI workflow and a repository validator.
- change: none to the skill — SKILL.md, agents, assets, references, scripts and tests are byte-identical to the v7 package.

**v7 - Cross-threat intelligence and correlation**

- add: data-breach intelligence — added DataBreaches.net, Have I Been Pwned, California AG, HHS OCR, and SEC EDGAR as breach evidence sources alongside existing cyber-news corroboration.
- add: cross-threat correlation — added evidence-gated correlation across ransomware, DDoS, data breaches, credential leaks, exploit activity, hacktivism, and vulnerability exploitation.
- change: actor identity resolution — verified aliases can be merged across sources while homonyms and conflicting threat-family identities remain separated.
- change: evidence semantics — live, historical, breach, and correlation records now use one consistent event/date/domain/provenance model, reducing false matches and duplicate counting.
- change: source coverage — successful findings no longer stop source collection early; relevant-source coverage must complete before final no-match or correlation conclusions.
- fix: fallback consistency — DDoS, breach, ransomware, and search-index recovery now keep source states and query semantics aligned across transport fallbacks.

**v6-universal - Integrated DDoS intelligence**

- add: DDoS tracker — integrated DDoSia Monitor to check recent hosts/targets, domain searches, date-based data, and DDoSia/NoName057 statistics while keeping DDoS targets separate from ransomware victims.
- add: cross-threat correlation — added profiles to correlate ransomware with DDoS, data breaches, credential leaks, exploit activity, hacktivism, and vulnerability exploitation using normalized identities and configurable time windows.
- change: threat routing — the skill now automatically distinguishes ransomware, DDoS, and mixed requests, applying maximum-effort only to relevant sources while keeping evidence separate across threat families.
- change: runtime resilience — live sources can now also be recovered through search indexes when APIs, feeds, or direct fetches are blocked by the runtime, with coverage and freshness explicitly disclosed.
- change: correlation semantics — cross-threat correlations now distinguish direct matches, campaign context, and rejected cases, separating temporal co-occurrence from causality.
- fix: DDoSia availability — runtime network blocks no longer automatically make DDoSia unavailable when current indexed evidence can still be recovered.
- fix: evidence classification — same-incident data breaches, credential dates, non-victim-specific exploit/CVE evidence, and data extortion are now classified separately to avoid improper counts or attribution.

**v5-universal - Unified tracker and trend analysis**

- add: intent routing — the skill automatically routes requests between Tracker for point lookups and Trend for historical, temporal, geographic, sector, financial, and legal analysis.
- add: historical intelligence — integrated local historical datasets for claims/victims, ransomware wallets, EuRepoC incidents, and the historical repository, combinable with live sources when the requested period requires it.
- add: trend analysis — added aggregations and comparisons by month, quarter, year, group, country, and sector, with explicit units of measure and preserved provenance.
- add: sector enrichment — when sector data is missing but required, the skill can retrieve it from the web using identity disambiguation, verifiable public sources, and enrichment provenance.
- change: unified runtime — Tracker and Trend now share the same maximum-effort live engine, fallback/replacement logic, and scripts.
- change: evidence semantics — claims, confirmed incidents, OSINT articles, EuRepoC records, wallets, and aggregate statistics remain distinct to avoid semantically incorrect counts or conclusions.

**v4-universal - Source resilience and functional fallbacks**

- add: replacement sources — added Ransomnews/Ransomtracker, Ransomfeed Web/RQL, VULONE, and ThreatVectr with distinct roles for claims, structured filtering, corroboration, and aggregate statistics.
- add: coverage validation — the skill verifies that all configured sources have been queried and that no safe retrieval paths remain untried before finalizing a response.
- change: source execution — every search uses all sources in maximum-effort mode, with no early exit after the first useful result and with transport or source fallbacks when available.
- change: provenance — reachability, freshness, functional equivalence, data type, and dataset independence are evaluated separately to avoid apparent corroboration or double counting.
- change: primary-source fallback — failures of ransomware.live and Ransomfeed now trigger functional replacement chains instead of immediately degrading to incomplete coverage.
- change: aggregate statistics — counts and rankings from different trackers are no longer merged automatically; coherent series or separate comparisons with explicit divergences are preferred.
- fix: source status — an unqueried source can no longer be marked UNAVAILABLE; statuses now require current-run evidence and replacements keep the primary source state separate.
- fix: runtime networking — repeated DNS/egress errors are now distinguished from individual source outages, and public resolvers remain diagnostic-only without altering routing or hostnames.
