# Threat-actor identity resolution

Use actor identity resolution before merging group/actor records across ransomware, DDoS, breach, hacktivism, exploit, or other threat families.

## Core rule

`EXACT NAME != SAME ENTITY`

and:

`DIFFERENT NAMES MAY BE THE SAME ENTITY ONLY WHEN ALIAS EQUIVALENCE IS SUPPORTED BY CURRENT EVIDENCE`

Do not use unrestricted fuzzy matching to merge actors.

## Evidence-driven behavior

Treat alias resolution as a runtime evidence problem, not as a fixed actor dictionary.

Use `scripts/actor_identity.py` only with caller-supplied verified actor records derived from current authoritative or high-quality threat-intelligence evidence. A record is eligible for deterministic resolution only when `verified: true` is explicitly set by the caller after evidence review.

Required record fields:
- `actor_id`
- `canonical_name`
- `aliases`
- `threat_families`
- `operation_types`
- `verified: true`

Recommended fields:
- `alias_confidence`
- `evidence`
- `notes`

The helper must not infer aliases from spelling similarity, substrings, headlines, vendor naming style, or shared TTPs alone.

## Resolution classes

- `RESOLVED_ALIAS` — the input maps to one verified canonical actor.
- `ENTITY_COLLISION` — the same normalized label maps to multiple verified actors; never merge without disambiguation.
- `UNRESOLVED` — supplied evidence does not establish an alias mapping; preserve the source label.
- `FAMILY_MISMATCH` — a verified actor name exists but the supplied threat-family hint conflicts with that identity; do not silently resolve.
- `VERIFIED_ALIAS_SET` — two labels resolve to the same canonical actor.
- `DISTINCT_ENTITY` — two resolved labels belong to different canonical actors.

Threat-family context may disambiguate an already-established collision, but it must not create an alias relationship by itself. If one verified name match exists and the supplied family conflicts with it, return `FAMILY_MISMATCH`.

## Illustrative examples only

The examples below are reasoning aids for the LLM. They are not a hard-coded actor catalogue, not exhaustive, and must not be treated as permanent truth. Re-verify them against current evidence before using them operationally.

### Example pattern A: homonym collision

A DDoS/hacktivist actor and a ransomware/extortion operation may share a very similar or identical-looking name. The correct behavior is:

`same-looking normalized name + distinct verified entities/families -> ENTITY_COLLISION -> DO NOT MERGE`

The previously discussed NoName case is an example of this pattern, not a special-case rule.

### Example pattern B: verified multi-vendor aliases

One actor may be named differently by different vendors. When current high-quality evidence explicitly establishes equivalence:

`different labels + verified alias evidence -> VERIFIED_ALIAS_SET -> merge canonical identity while preserving source labels`

The previously discussed Luna Moth / Silent Ransom Group / Chatty Spider naming case is an example of this pattern, not a built-in mapping.

## Cross-source behavior

Before deduplicating victims or correlating records by actor:

1. Gather current alias/identity evidence.
2. Build explicit verified actor records.
3. Resolve each source label against those records.
4. Merge only `VERIFIED_ALIAS_SET` identities.
5. Keep `ENTITY_COLLISION` records separate.
6. Keep `UNRESOLVED` labels separate unless later evidence establishes equivalence.
7. Preserve original source labels and provenance after canonicalization.
8. Never count multiple vendor aliases of one verified actor as multiple independent actors.
9. Never infer operational equivalence or causality from a shared word, TTP, infrastructure class, or naming convention alone.

## Updating evidence

Prefer current authoritative or high-quality threat-intelligence sources. Alias evidence can change over time as vendors rename, split, merge, or re-scope clusters. Treat canonicalization as revisable and evidence-bound rather than permanent.
