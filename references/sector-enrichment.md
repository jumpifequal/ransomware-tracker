# Conditional sector enrichment

Use this workflow only when the user's requested output materially depends on sector information and the victim record has no sector.

## Trigger

Enrich sector only when all are true:

- the user asks for sector analysis, sector filtering, sector ranking, a sector field, or another result that cannot be completed correctly without sector;
- the record has a usable victim name;
- the sector is missing from the bundled/live record.

Do not enrich sector merely because the field is empty in a response where sector is irrelevant.

## Web workflow

1. Use host-native web search/fetch; do not reintroduce legacy GPT Actions.
2. Search the victim's exact name with available disambiguators such as organization, domain, country, location, or known role.
3. Prefer first-party and authoritative public sources: official website, employer page, company registry, professional registry, or government source.
4. Use reputable media or industry directories only when the identity and sector are explicit.
5. For a natural person, require identity disambiguation beyond name alone before assigning sector.
6. Require explicit sector/industry/employer evidence; do not infer sector from surname, social graph, article adjacency, ransomware group, domain wording, or weak contextual clues.
7. If evidence conflicts or remains ambiguous, leave sector unavailable.
8. Record provenance for enriched values: source URL, source type, confidence, and that the value was web-enriched.
9. Never infer or enrich sensitive traits unrelated to the requested sector field.

## Output semantics

An enriched sector is supplementary metadata, not part of the original ransomware source record. When material to the answer, mark it as web-enriched and cite the supporting public source.

For trend aggregation, include web-enriched sectors only when the identity match and sector evidence satisfy this gate. Otherwise classify the record as sector unknown rather than excluding or guessing.
