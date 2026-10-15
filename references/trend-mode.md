# Trend analysis mode

Use for aggregation, comparison, time series, rankings, sector/geography analysis, historical analysis, wallet/ransom analysis, EuRepoC/legal views, or multi-period questions.

## Evidence model

Combine:
- bundled historical datasets;
- the same live-source scripts and replacement/fallback engine used by Tracker mode;
- OSINT confirmation sources where incident confirmation or enrichment is required.

Never treat the historical bundle as a substitute for fresh live collection when the requested period extends beyond its coverage.

## Analytics rules

1. Normalize before aggregation.
2. Deduplicate claim-like records before counting.
3. State exactly what is counted: claim/victim record, confirmed incident, wallet observation, EuRepoC incident, or aggregate statistic.
4. Do not merge EuRepoC incidents, wallet records, leak-site claims, and media reports into one numeric series.
5. For cross-source trends, prefer one coherent series; use separate comparisons or explicit ranges when trackers diverge.
6. Preserve source lineage and do not count likely derivative trackers as independent corroboration.
7. Use monthly or quarterly granularity when the data supports it and the request asks for trends.
8. For charts, chart only verified computed values and retain the same definition across the series.
9. When live data extends the historical period, merge only records that can be normalized to the same semantic record type and deduplicate by victim/group/date plus provenance-aware rules.
10. Report data-coverage boundaries when they materially affect interpretation.

Use only configured source adapters and host-native web transports.

## Missing sector during trend analysis

When a sector-dependent analysis contains records with missing sector, follow `references/sector-enrichment.md` only for records whose sector materially affects the requested calculation. Keep unresolved records in an explicit unknown sector bucket rather than guessing or silently dropping them.

## DDoS trend analysis

For DDoSia trend/statistics requests, use the DDoSia statistics/date operations and DDoS source scope.

Supported semantic units include DDoSia target observations, unique hosts/IPs, request counts, and documented time-series aggregates returned by the source. Never combine these numerically with ransomware victims/claims. Cross-threat comparisons must use separate series and explicit labels.

### DDoSia transport fallback

For DDoSia period/trend requests, use search-index recovery after direct fetch failures. Indexed snapshots may support verified partial results, but never imply full-period completeness unless the evidence is exhaustive.
