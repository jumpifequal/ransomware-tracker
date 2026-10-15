# Tracker mode

Use for entity-centric and current-record questions: named victim/company/domain, named ransomware group, recent claims, specific country/date lookup, or direct verification.

## Execution

1. Use the shared live-source engine and maximum-effort policy.
2. Consult every configured live source/surface unless the user explicitly constrains sources.
3. Use the local historical claims datasets when the requested period predates live coverage or when an older entity lookup benefits from historical evidence.
4. Keep claim records, confirmed incidents, journalistic confirmations, and aggregate statistics distinct.
5. Return record-level evidence and the mandatory source-status footer.

Use the bundled Python helpers and host-native web transport. Do not assume any additional integration is configured.

## Missing sector

If the user explicitly needs the sector and the matched victim has no sector, follow `references/sector-enrichment.md`. Do not perform sector enrichment for unrelated lookups.

## DDoS tracking

For requests about DDoS, DDoSia, NoName057, or whether a host/domain appears among DDoSia targets, use `scripts/ddosia.py` and the DDoS source scope.

Do not query ransomware sources merely to satisfy DDoS coverage unless the user asks for ransomware too. For generic cross-threat exposure checks, use mixed scope and keep ransomware findings separate from DDoS target observations.

A DDoSia target observation means the host was identified as a potential/intended DDoS target by the monitored DDoSia ecosystem. It is not, by itself, proof of attack execution, success, outage, or compromise.

### DDoSia transport fallback

If DDoSia direct API/Web fetch is blocked, use the search-index recovery policy in `references/ddosia-runtime-fallback.md` before reporting DDoSia unavailable.
