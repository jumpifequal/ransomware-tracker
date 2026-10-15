# Unified data model

Use one canonical event contract across live and historical claim-like records. Source adapters may accept legacy/source-specific field names, but downstream filtering, deduplication, and correlation operate on the canonical fields below.

## Canonical event record

- `victim` — victim/entity label when present.
- `organization` — explicit organization field when distinct from victim.
- `group` — source-reported ransomware/group label.
- `actor` — source-reported actor label when distinct from group.
- `canonical_actor_id` — verified canonical actor identity only.
- `actor_identity_status` — identity resolution status such as `RESOLVED_ALIAS`; do not populate from name similarity alone.
- `date` — canonical event/reference date used by downstream filters.
- `date_semantics` — meaning of `date`, such as `claim_date`, `discovery_date`, `publication_date`, `breach_date`, or `source_date`.
- `country`
- `sector`
- `domain` — hostname/domain only; never collapse it into `url`.
- `url` — evidence or source URL.
- `data_type` — semantic unit, for example `ransomware-claim-record`, `media-report`, or `data-breach-evidence`.
- `source` — primary acquisition source for the record.
- `provenance` — ordered unique list of source/dataset lineage labels.
- `raw_id` — source record identifier when available.

`published_at` and `record_type` are accepted only as source/legacy inputs. Do not emit them as parallel canonical output fields.

## Canonical source-state contract

Allowed runtime source states:
- `OK`
- `EMPTY`
- `BLOCKED`
- `RATE_LIMITED`
- `UNAVAILABLE`
- `INVALID_RESPONSE`
- `NOT_TESTED`

Use `NOT_TESTED` only for material unattempted coverage. Use the shared deterministic contract helper so transport, status rendering, and coverage validation do not maintain divergent state vocabularies.

## Non-claim datasets

Keep these separate from claim records:
- wallet observations and transactions;
- EuRepoC cyber incidents and legal/attribution fields;
- historical repository incident records;
- journalistic OSINT confirmations;
- aggregate statistics from tracker/reporting surfaces.

## Semantic distinction

`claim/victim record != confirmed incident != media report != EuRepoC incident != wallet transaction != aggregate statistic`

Always label the semantic unit being counted.

## Canonical DDoS target observation

Keep DDoS observations separate from ransomware claim records.

Fields when returned by the source:
- `host`
- `ip`
- `type`
- `method`
- `port`
- `use_ssl`
- `path`
- `detected_at`
- `imported_at`
- `source`
- `data_type = ddosia-target-observation`

Semantic rule:

`DDoS target observation != confirmed DDoS attack != successful outage != ransomware victim/claim`

## Correlation adapter rule

Before sending claim-like records into cross-correlation:
1. map the event/reference date to `date` and preserve its meaning in `date_semantics`;
2. keep `domain` separate from evidence `url`;
3. attach `canonical_actor_id` only after verified actor resolution;
4. preserve provenance after deduplication;
5. do not use publication/catalog/reporting dates as incident dates when a better event date exists.
