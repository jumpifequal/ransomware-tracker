# Runtime search-index fallback

Use this policy for configured live sources when direct transports are blocked by the execution environment.

A proxy `403`, egress denial, DNS/TLS failure, robots denial, timeout, or unavailable browser/computer is a **transport limitation**. It is not, by itself, proof that the source is globally unavailable.

## Global ladder

For every configured live source, use this order when applicable:

1. source-specific Python/API/feed helper;
2. exact endpoint through host-native web transport;
3. verified public page/feed for the same source;
4. **search-index recovery** using the host's web search/search engine;
5. configured functional replacement source where defined;
6. corroborating OSINT where useful;
7. provenance and coverage disclosure.

Do not skip a configured source solely because its direct transport is blocked if search-index recovery remains safely available.

Use `scripts/search_index_fallback.py` to generate stable source-specific search queries when useful. DDoSia may continue to use its dedicated helper for country-month recovery.

## Qualification gate

Indexed evidence is usable only when all relevant conditions hold:

- the result is attributable to the intended source/domain;
- the indexed content contains substantive evidence, not just a generic title;
- freshness matches the requested period;
- the retrieved text supports the exact claim being made;
- the semantic unit remains explicit;
- the indexed material is not silently treated as an exhaustive dataset.

A search result page or snippet is a transport for source evidence, not a new independent source.

## Status semantics

Separate:

- source availability;
- direct transport availability;
- search-index availability;
- freshness;
- completeness;
- functional equivalence;
- dataset independence.

If direct transports fail but fresh, useful indexed source content is recovered, the source can be `🟢 OK` with channel `Search index`. Preserve the failed direct transports in the note.

If indexed content is stale or only partially covers the request, keep the source usable but disclose `partial coverage`. Do not present it as a complete period or complete dataset.

If every safe supported path, including search-index recovery and configured replacements, is exhausted without usable evidence, then assign the terminal non-success state.

## Source-specific guidance

### Structured ransomware trackers

Applies to ransomware.live, Ransomfeed, RansomLook, Ransomnews/Ransomtracker, and VULONE.

Search by victim, group, country, date/month, or free-text entity. Preserve claim/victim semantics and do not infer confirmed incident status from indexed tracker content.

Search-index recovery does not prove dataset independence. Lineage/overlap rules still apply.

### ThreatVectr

Use indexed content for aggregate trend/ranking/statistics recovery only. Do not upgrade it to victim-level evidence unless a direct victim record is explicitly exposed.

### Editorial OSINT

Applies to BleepingComputer, Cybernews, and Security Affairs.

When feed/page fetch fails, search the source domain directly through the search index before returning `EMPTY` or `UNAVAILABLE`.

For editorial sources:
- `EMPTY` requires a completed search attempt for the requested entity/period, not merely a failed feed fetch;
- a current indexed article may be `OK / Search index`;
- absence from indexed results is not proof that no incident occurred globally.

### DDoSia Monitor

Use the same global rules plus the dedicated DDoSia period-completeness policy. DDoS target observation remains distinct from confirmed attack success or outage.

## Coverage rule

Maximum-effort execution means every configured source in the relevant threat scope must exhaust all safe supported retrieval paths that are actually available in the runtime.

`NOT TESTED` is not acceptable merely because a preferred direct transport failed.
