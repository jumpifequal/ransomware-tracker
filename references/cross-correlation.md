# Cross-correlation module

Use this isolated module only for relationships, overlap, co-occurrence, intersection, or connection between different cyber-event families. Keep ordinary single-family Tracker/Trend execution independent from it.

## Core rule

Accept a candidate only when:

`resolved entity match + temporal window + profile-specific evidence gate`

Correlation means temporal co-occurrence / correlated exposure, not causality.

Classify:
- `DIRECT`: same resolved victim/entity and victim-specific evidence on both sides.
- `CONTEXTUAL`: same victim/entity but second-side evidence is actor/campaign/product-level.
- `REJECTED`: evidence is too weak or the profile's victim-specific gate is not satisfied.

Only `DIRECT` contributes to strict incident-level correlation counts.

## Entity resolution

Normalize organization/victim names, legal suffixes, hostnames, and explicit aliases conservatively. Support an explicit alias map. Do not use unrestricted fuzzy matching. Parent/subsidiary or brand/legal-entity relationships require explicit evidence.

## Date semantics

Preserve the date field used. For credential events prefer:
1. `credential_used_date`
2. `credential_published_date`
3. `credential_discovered_date`
4. `credential_stolen_date`
5. generic `date`

Use elapsed time from total seconds for tolerance boundaries.

## Relation taxonomy

Return:
- `same_incident`
- `temporal_cooccurrence`
- `campaign_context`

For ransomware↔data-breach, do not count the exfiltration component of the same ransomware/extortion incident as an independent cross-threat incident.

## Ransomware/extortion taxonomy

Use:
- `ransomware_encryption`
- `data_extortion`
- `ransomware_or_extortion`

Do not treat every leak-site/extortion claim as confirmed encryption.

## Profiles

### ransomware_ddos
Default ±14 days. Same victim/organization/domain. Actor equality may strengthen confidence but is not required.

### ransomware_data_breach
Default ±30 days. Detect `same_incident` when case/incident evidence establishes one incident.

### ransomware_credential_leak
Default ±30 days. Use credential-specific date semantics. Never infer that leaked credentials caused ransomware.

### ransomware_exploit_activity
Default ±21 days. `DIRECT` requires victim-specific exploit evidence. Actor/campaign exploitation knowledge is only `CONTEXTUAL`.

### ddos_hacktivism_campaign
Default ±14 days. Explicit campaign target membership may produce `DIRECT`. Country, sector, or broad campaign membership alone is insufficient.

### ransomware_vulnerability_exploitation
Default ±30 days. `DIRECT` requires victim-specific exploitation evidence or an explicit source linking the vulnerability to that victim. Actor/group CVE knowledge alone is `CONTEXTUAL`. Never infer initial-access vector without explicit evidence.

## Deduplication and event clustering

Prefer a canonical event id. Otherwise cluster by event family + resolved entity + date + actor/group + provenance hints. Do not count multi-source duplicates as independent events, and do not merge distinct incidents solely because they share a date.

## Confidence

Combine entity strength, temporal proximity, evidence specificity, source quality, and actor/campaign alignment. Temporal proximity alone cannot produce high confidence.

## Metrics

When denominators are known, keep separate:
- victim correlations;
- DIRECT event correlations;
- contextual correlations;
- ransomware-side correlation rate;
- other-side correlation rate.

## Extensibility

New profiles belong only in this isolated module. Define event families, match keys, tolerance, date semantics, evidence gate, deduplication, relation semantics, optional actor/campaign boost, and prohibited causal inference.


## Actor identity gate

Resolve actor/group labels before using actor equality as a confidence boost. Read `actor-identity.md`.

- Verified aliases of the same actor may satisfy actor equality.
- `ENTITY_COLLISION` or unresolved homonyms must not satisfy actor equality.
- Preserve source labels and canonical actor id separately.
- Actor equality never establishes causality by itself.


## Actor identity gate

Resolve actor/group labels before using actor equality as a confidence boost.

Actor boost is allowed only when both records carry the same verified `canonical_actor_id` and `actor_identity_status = RESOLVED_ALIAS`.

Raw actor/group string equality must not create actor boost because homonyms can collide and vendor aliases can differ. `ENTITY_COLLISION`, `FAMILY_MISMATCH`, and unresolved labels do not satisfy actor equality.

Actor equality never establishes causality by itself.
