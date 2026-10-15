# Source map and helper interfaces

All source helpers emit one JSON object with:

```json
{
  "ok": true,
  "state": "OK",
  "source": "source-name",
  "request": {"operation": "operation-name"},
  "status": 200,
  "data": {},
  "error": null
}
```

Allowed source states:

- `OK` — usable data returned.
- `EMPTY` — request succeeded but produced no records.
- `BLOCKED` — automated/authenticated access was refused, such as HTTP 401/403.
- `RATE_LIMITED` — the source is reachable but throttling requests, such as HTTP 429.
- `INVALID_RESPONSE` — request/endpoint contract is invalid, such as HTTP 400/404/405/410/422.
- `UNAVAILABLE` — network, timeout, or transient server failure.
- `NOT_TESTED` — material source was not attempted; this is a coverage failure for unrestricted relevant scope.

Never interpret `BLOCKED`, `INVALID_RESPONSE`, or `UNAVAILABLE` as evidence that no incident exists.

## ransomware.live

Base URL: `https://api.ransomware.live/v2`

Helper: `python scripts/ransomware_live.py`

Current free-v2 operations:

- `recent` → `/recentvictims`
- `groups` → `/groups`
- `group NAME` → `/group/{name}`
- `group-victims NAME` → `/groupvictims/{name}`
- `month YEAR MONTH` → `/victims/{year}/{month}`
- `country CODE` → `/countryvictims/{code}`
- `sector SECTOR` → `/sectorvictims/{sector}`
- `search KEYWORD` → client-side substring search over `/recentvictims`

Do not use the obsolete `/searchvictims/{keyword}` assumption.

For searches outside the recent feed, use month/country/group endpoints and then `normalize_records.py` plus `filter_records.py`.

## Ransomfeed

Base URL: `https://api.ransomfeed.it`

Helper: `python scripts/ransomfeed.py`

Current operations:

- `recent --limit N` → `/offset/{N}`
- `search KEYWORD --limit N` → `/search/{term}/offset/{N}`
- `country COUNTRY --limit N` → `/country/{country}/offset/{N}`
- `gang GANG --limit N` → `/gang/{gang}/offset/{N}`
- `year YYYY --limit N` → `/date/{year}/offset/{N}`
- `combined [--keyword] [--country] [--gang] [--year] [--limit]` → composed path filters

The Ransomfeed API uses path-composable filters; do not use `/v1/victims`.

## RansomLook

Base URL: `https://www.ransomlook.io`

Helper: `python scripts/ransomlook.py`

Operations:

- `recent` → `/api/recent`
- `groups` → `/api/groups`
- `group NAME` → `/api/group/{name}`
- `leaks` → `/api/leaks`
- `leak ID` → `/api/leaks/{id}`
- `search QUERY` → `/api/search/?q=...`

When a recent result window is too narrow, explicitly report limited temporal coverage and widen with available historical/search operations rather than treating the recent feed as exhaustive.


## DDoSia Monitor

Base URL: `https://ddosia.rfeed.it`

Helper: `python scripts/ddosia.py`

The platform tracks targets identified by the DDoSia botnet associated with NoName057. Treat these as **DDoS target observations / intended targets**, not proof that a DDoS attack succeeded.

Operations:

- `recent --limit N` → `/api/recent_targets.php?limit=N`
- `search HOST` → `/api/search_host.php?host=HOST`
- `date YYYY-MM-DD` → `/api/targets_by_date.php?date=YYYY-MM-DD`
- `dates` → `/api/available_dates.php`
- `stats overview|by_year|by_month|by_day|timeseries_monthly|timeseries_daily` → `/api/stats.php?type=...`

Public web fallbacks:

- dashboard/recent/statistics → `https://ddosia.rfeed.it/index.php`
- host search → `https://ddosia.rfeed.it/search.php`
- date navigation → `https://ddosia.rfeed.it/calendar.php`

Use channel `API` for direct helper retrieval, `Web→API` for the exact API endpoint fetched by host-native web transport, `Web` for public-page fallback, and `Search index` when a search engine returns usable indexed DDoSia content after direct transports fail.

**Search-index fallback:** after API/Web→API/Web failures caused by runtime restrictions, search indexed DDoSia dashboard/search/calendar content before declaring the source unavailable. Read `references/ddosia-runtime-fallback.md`.

Never merge DDoS target counts with ransomware victim/claim counts. If the user requests a cross-threat comparison, present the series separately with their semantic units.

## BleepingComputer

Helper: `python scripts/bleepingcomputer.py`

Operations:

- `ransomware-tag`
- `security-news`
- `feed`
- `search QUERY`

The shared transport now extracts RSS items and HTML metadata (`title`, `description`, publication metadata, canonical URL) before falling back to link candidates.

## Cybernews

Helper: `python scripts/cybernews.py`

Operations:

- `security`
- `news`
- `feed`
- `search QUERY`

HTTP 403 is represented as `BLOCKED`. Do not immediately retry a blocked request and do not attempt to bypass anti-bot or WAF controls. Continue with other permitted OSINT sources.

## Security Affairs

Helper: `python scripts/security_affairs.py`

Operations:

- `ransomware-tag`
- `feed`
- `search QUERY`

## Deterministic processing adapters

### Normalize records

```text
source-helper JSON
→ python scripts/normalize_records.py --source SOURCE
→ canonical JSON records
```

Canonical fields:

`victim`, `organization`, `group`, `actor`, `canonical_actor_id`, `actor_identity_status`, `date`, `date_semantics`, `country`, `sector`, `domain`, `url`, `data_type`, `source`, `provenance`, `raw_id`

### Filter and deduplicate

```text
canonical JSON
→ python scripts/filter_records.py [--keyword ...] [--country ...] [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]
```

Deduplication key: normalized `(victim/organization, group/canonical_actor_id, date)`.

Cross-source matches preserve the canonical `provenance` list.

### Fallback policy

```text
[array of API source envelopes]
→ python scripts/fallback_policy.py
```

The adapter summarizes the current retrieval layer and always returns `RUN_REMAINING_COVERAGE`; only the coverage gate can authorize completion.

## Native web transport manifest

When Python cannot resolve or reach external hosts, generate the exact request URL with:

```text
python scripts/request_manifest.py SOURCE OPERATION [VALUE]
```

The returned URL must be fetched through the host's native web/browser/fetch capability.

Examples:

```text
python scripts/request_manifest.py ransomware.live recent
python scripts/request_manifest.py ransomware.live group-victims lockbit5
python scripts/request_manifest.py ransomfeed search hospital
python scripts/request_manifest.py ransomlook search Synnovis
```

This fallback changes the transport channel, not the source. If the exact API URL is successfully retrieved through the native web channel, preserve the original API source attribution.

### ransomware.live semantic 404

For month queries, inspect the bounded HTTP error body before classifying a 404.

- HTTP 404 whose body contains `No victims found` → `EMPTY`; the endpoint is valid and returned no records for that period.
- HTTP 404 with an unrelated/generic route-not-found body → `INVALID_RESPONSE`.

Never classify a month query as invalid from status code alone.

## HTTP request profiles

Use content-specific browser-compatible request profiles instead of one global Accept header.

- `api` — `User-Agent: Mozilla/5.0`, `Accept: application/json, text/plain, */*`
- `rss` — `User-Agent: Mozilla/5.0`, `Accept: application/rss+xml, application/atom+xml, application/xml, text/xml, */*`
- `html` — `User-Agent: Mozilla/5.0`, `Accept: text/html, application/xhtml+xml, */*`

Use `api` for ransomware.live, Ransomfeed, and RansomLook. Use `rss` for feed operations and `html` for public article/search pages.

The custom helper User-Agent must not be used as the default fingerprint because a raw diagnostic GET with the browser-compatible profile succeeds against ransomware.live. Do not add additional browser-only headers unless a source specifically requires them.

For deployment diagnostics run:

```text
python scripts/diagnose_source.py ransomware.live recent
python scripts/diagnose_source.py ransomfeed search hospital
python scripts/diagnose_source.py ransomlook search Synnovis
```

## Verified transport routes

Use the following source-specific route policy.

| Source | Primary route | Verified public fallback |
|---|---|---|
| ransomware.live | exact API endpoint | retry the same canonical URL through another available transport; otherwise continue with alternate ransomware sources |
| Ransomfeed | exact API endpoint | none required |
| RansomLook | exact API endpoint | `https://www.ransomlook.io/recent` for recent-post fallback |
| BleepingComputer | feed/search helper | `https://www.bleepingcomputer.com/tag/ransomware/` |
| Cybernews | security/search helper | `https://cybernews.com/security/` |
| Security Affairs | feed/search helper | `https://securityaffairs.com/tag/ransomware` |
| DDoSia Monitor | exact API endpoint | dashboard/search/calendar public pages on `ddosia.rfeed.it` |

Rules:

1. Prefer the primary source helper.
2. If local Python transport fails, try the exact API URL through Web→API.
3. If an exact API/feed URL is unavailable through the host web transport and a verified public fallback exists, use that public page as OSINT fallback.
4. A successful public-page fallback does not count as API coverage.
5. Do not classify a source as invalid merely because one transport channel cannot open it.
6. For ransomware.live monthly queries, build the exact route as `/v2/victims/{year}/{month}` and support both one- and two-digit months.

## Rate limiting

Treat HTTP 429 as `RATE_LIMITED`, never as `INVALID_RESPONSE` or generic source unavailability.

For ransomware.live, the observed public response can state `1 per 1 minute`. When that message is present and no usable `Retry-After` header is supplied, wait 65 seconds before a retry. If `Retry-After` is supplied as seconds, honor it with a small safety margin.

Do not issue parallel duplicate requests to the same source/operation in one run. Reuse an already acquired response whenever possible.

## Transport portability

Transport outcomes are environment-specific. A Python DNS failure, host-web fetch failure, browser success, or command-line success describes that runtime only.

Do not convert a runtime observation into a permanent source rule. For each source, preserve the canonical request and choose among available transports at execution time:

1. direct Python GET;
2. exact API URL through host web transport, when available;
3. public OSINT fallback where configured.

A transport failure is not evidence that the source endpoint is invalid.

## DNS/egress interpretation

Repeated `gaierror` or equivalent DNS failures across unrelated source domains indicate a probable runtime-level resolver/egress condition.

If both direct UDP and TCP probes to an explicitly configured public resolver also fail, treat that as stronger evidence of sandbox egress restriction rather than public DNS failure. Do not use returned IP addresses to replace canonical HTTPS hostnames.

## Replacement source map

| Source/surface | Primary role | Data type | Independence / lineage |
|---|---|---|---|
| RansomLook | claims primary/corroboration | victim records, groups, dates, history | unknown; do not infer independence |
| Ransomnews/Ransomtracker | ransomware.live replacement | victim/claim records, groups, dates, aggregates | possible overlap with RansomLook |
| Ransomfeed Web/RQL | Ransomfeed API replacement surface | structured victim/group/country/date/sector queries | same Ransomfeed family |
| VULONE | tertiary corroboration | victim/group/date/geography/statistics | partial overlap; public pages describe cross-checking |
| ThreatVectr | aggregate sanity check | trends, rankings, monthly statistics | derived aggregate lineage; not victim-level |
| RansomWatch GitHub | not current fallback when stale | historical JSON | freshness gate can disqualify |

Treat reachability, freshness, equivalence, and independence as separate fields.

## Global search-index recovery

When direct helper/API/feed/Web transports fail because of runtime restrictions, use `scripts/search_index_fallback.py` before declaring the source unavailable, provided host-native web search is available.

Supported profiles:

- ransomware.live
- Ransomfeed
- RansomLook
- Ransomnews/Ransomtracker
- VULONE
- ThreatVectr
- BleepingComputer
- Cybernews
- Security Affairs
- DDoSia Monitor

Use channel `Search index`. Indexed evidence remains attributed to the original source and does not create an independent corroborating dataset.

Read `references/runtime-search-index-fallback.md` for freshness, completeness, and status rules.


## Data-breach intelligence sources

Helper: `python scripts/breach_sources.py`

### DataBreaches.net
- `feed` → `/feed/`
- `search ORGANIZATION` → site search
- authority: `SPECIALIST_OSINT`

### Have I Been Pwned
- `breaches` → public breach catalogue
- `latest` → latest breach
- `breach NAME` → named breach
- authority: `STRUCTURED_CATALOGUE`
- preserve breach and catalogue-added dates separately.

### California AG
- `list` → public breach notice list
- `search ORGANIZATION` → organization-filtered list
- authority: `REGULATORY`
- preserve breach and reported dates separately.

### HHS OCR
- `portal` → public breach portal
- authority: `REGULATORY`
- preserve portal/reporting scope when drawing aggregate conclusions.

### SEC EDGAR Item 1.05
- `filings` → EDGAR filing search surface
- authority: `PRIMARY_DISCLOSURE`
- preserve filing date separately from incident dates stated in the filing.

Dedicated breach sources inherit the same transport hierarchy:
`helper/API/RSS → exact Web transport → public page/data surface → Search index → corroboration`.

Do not treat publication, filing, reported, or catalogue-added dates as incident dates unless no event date exists and the confidence downgrade is explicit.
