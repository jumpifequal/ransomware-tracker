# Operating rules

## Runtime loading

Always load this file and `source-map.md` for normal execution.

Load `python-discipline.md` only when maintaining, modifying, testing, or reviewing the bundled Python code. It is not required for an ordinary ransomware lookup.

## Default source sequence

Use:

`API acquisition → deterministic normalization/filtering → fallback decision → OSINT fallback/enrichment`

unless the user explicitly requests API-only, OSINT-only, or a named source.

Primary API layer:

1. ransomware.live
2. RansomLook
3. Ransomfeed

Fallback/enrichment OSINT layer:

1. BleepingComputer
2. Cybernews
3. Security Affairs

## Source-state semantics

Never collapse all failures into one status.

- `OK`: usable data.
- `EMPTY`: successful request with no records.
- `BLOCKED`: automated access refused.
- `INVALID_RESPONSE`: endpoint/request contract invalid or response unusable.
- `UNAVAILABLE`: source could not be reached reliably.

Only `EMPTY` can contribute to a "no API match" conclusion. The other failure states mean coverage is incomplete.

Run `fallback_policy.py` after the API layer.

## Matching and filtering

Do not manually perform deterministic matching when the processing adapters are available.

Required flow:

1. Run source helper.
2. Normalize successful records with `normalize_records.py`.
3. Filter with `filter_records.py`.
4. Deduplicate by canonical victim/group/date.
5. Preserve corroborating source names.

Use case-insensitive partial matching for vendor/victim names.

Apply country/date filters only when the source supplies verifiable values. A record with unknown geography must not satisfy a country-specific query.

## Temporal coverage

Prefer the most recent data first.

When a source exposes only a recent window:

1. state the actual temporal limitation;
2. widen using source-supported month/year/search operations when necessary;
3. do not claim "no historical match" from a short recent feed.

## OSINT fallback

Run OSINT when the API layer:

- produces no matching records;
- has blocked/unavailable/invalid sources;
- has insufficient temporal coverage for the user's requested period.

Tell the user when the answer relies on OSINT because API coverage was empty or incomplete.

For Cybernews, treat HTTP 403 as `BLOCKED`; do not attempt WAF bypass.

## OSINT interpretation boundary

Python performs:

- HTTP transport;
- RSS/XML parsing;
- HTML metadata extraction;
- deterministic link extraction;
- canonical field mapping;
- filtering;
- deduplication;
- fallback-state decisions.

The model performs:

- user intent interpretation;
- semantic judgment about whether an article actually reports a ransomware/breach event;
- ambiguous entity resolution;
- distinction between direct victim, supply-chain victim, and incidental mention;
- final explanation.

Never infer a ransomware attribution from article adjacency, tags alone, or unrelated snippets.

## Anti-hammering

The transport performs at most three attempts for transient failures.

Actual retry waits are:

- after first transient failure: 5 seconds;
- after second transient failure: 15 seconds;
- after third failure: stop and change source/fallback.

Do not add immediate manual retries on top of helper retries.

## User source override

- API-only: do not run OSINT fallback.
- OSINT-only: skip API acquisition.
- Named source only: restrict to that source and report narrower evidence coverage.

## Transport fallback: mandatory hybrid acquisition

Local Python network access is optional, not assumed.

Use this acquisition order:

1. Attempt the source-specific Python helper.
2. If the failure is DNS, socket/network egress, or equivalent runtime-level transport failure, do not conclude that the source is unavailable.
3. Build the exact allow-listed request with `request_manifest.py`.
4. Use the host runtime's native web/browser/fetch capability to retrieve that URL.
5. Feed the retrieved JSON/text back into the deterministic normalization/filtering pipeline when possible.
6. Mark collection mode as `NATIVE_WEB_FALLBACK`.
7. Report API/source coverage accurately: transport fallback preserves source coverage when the exact API URL was fetched successfully.

Do not repeatedly retry local Python after a runtime-wide DNS failure has been established.

A native web/browser fetch of the exact API endpoint is considered API-source coverage; a general search-engine result about that API is not.

## Runtime transport capability

Determine transport availability during the current execution. Do not reuse a previous session's transport failure as a permanent rule.

If direct Python fails at the transport layer, attempt an equivalent supported transport with the same canonical request. If no alternate transport is available, continue with other configured sources and mark coverage incomplete.

## Current-run source ledger

Maintain source status only from attempts made during the active execution.

For each configured source record:

- whether a request was actually attempted;
- state returned by the helper/tool;
- channel used;
- HTTP status or transport exception when applicable;
- whether usable data was acquired.

Never carry a source failure state forward from an earlier conversation turn or another runtime. Never convert "not called" into `UNAVAILABLE`.

Before producing the mandatory status footer, validate the rows with `scripts/source_status.py` when deterministic execution is available. If an unqueried source is material to interpreting coverage, show it as `NOT TESTED`; otherwise omit it.

## Runtime-wide transport failure

If multiple unrelated source domains fail with the same resolver/egress error in the current run, record one aggregate runtime diagnosis, but still attempt every configured source at least once; avoid only redundant retries after per-source evidence exists.

Use the bundled network diagnostic helper only to determine whether the failure is local resolver-specific or broader egress restriction. Public resolvers are diagnostic probes only and must not be used to replace source hostnames or bypass runtime controls.

A runtime-wide transport failure does not establish that any source itself is unavailable.

## Maximum-effort source execution

For unrestricted operational runs, consult every configured source and exhaust every safe supported retrieval path for that source before assigning a terminal failure state.

Per source, use this progression when applicable:

1. source-specific Python helper;
2. bounded retry for transient failures;
3. alternate supported transport using the same canonical request;
4. verified public page/feed fallback for that source.

Do not stop because another source already returned sufficient data. Do not emit a final answer while an untried safe retrieval path remains.

Maximum effort is bounded by source rate limits, retry policy, platform capabilities, and access-control constraints. Never bypass WAF/authentication/anti-bot controls and never loop indefinitely.

## Functional replacement before incomplete coverage

Do not degrade immediately to incomplete coverage when ransomware.live or Ransomfeed fails at DNS, egress, TLS, web fetch, WAF/CDN, or another runtime layer.

Preserve the failed primary source state, then exhaust qualified functional replacements. Record replacement reachability, freshness, functional role, independence/lineage, and data type separately.

Use replacement qualification rather than HTTP reachability alone. A stale but reachable dataset does not satisfy current-period coverage.

For claims/victim records, prefer victim-level sources. For aggregate statistics, preserve one coherent series rather than summing across trackers.

## Search-index recovery

When direct transports fail, attempt host-native search-index recovery before a terminal unavailable state if search is available. Preserve direct transport failures separately from source reachability. Indexed results must be fresh, attributable, semantically valid, and explicitly partial when they do not establish full-period coverage.
