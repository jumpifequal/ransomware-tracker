# DDoSia runtime fallback

Direct reachability of `ddosia.rfeed.it` is runtime-dependent. A Python proxy `403`, browser/WebFetch timeout, robots denial, or unavailable computer/browser is a **transport limitation**, not evidence that DDoSia Monitor itself is down.

## Required ladder

For DDoSia requests, try in this order:

1. Python helper/API.
2. Exact API endpoint through host-native web transport.
3. Public DDoSia dashboard/search/calendar page through host-native web fetch.
4. **Search-index recovery**: use the host's web search/search engine to retrieve indexed DDoSia pages or snippets.
5. Corroborating OSINT for the same DDoS campaign/target where useful.

Do not stop at step 3 solely because direct fetch is blocked.

Use `scripts/ddosia_search_fallback.py` to generate stable search queries for host, date, recent, or country-month requests when useful.

## Search-index rules

Search-index recovery is valid only when:

- the result clearly identifies a `ddosia.rfeed.it` page or otherwise explicitly attributes the data to DDoSia Monitor;
- the indexed/crawled freshness is compatible with the user's requested period;
- the retrieved text contains usable DDoSia evidence, not just a title or generic description;
- exact values, hosts, dates, methods, or country information are taken from the indexed content, not inferred.

Use channel `Search index`.

If useful current-run DDoSia content is recovered from the search index, report DDoSia Monitor as `🟢 OK` on channel `Search index`, while preserving the failed direct transports in the note.

If the search index only provides stale or partial material, do not call the requested period complete. State the coverage limit explicitly.

## Period completeness

For requests such as “quali DDoS ci sono in Italia questo mese”:

- try country + month searches against DDoSia-indexed pages;
- retrieve every useful current-period result available from search;
- corroborate named targets via independent OSINT when useful;
- if the complete monthly target set cannot be reconstructed, return the verified subset and label it `partial coverage`;
- never convert a last-24-hours dashboard pulse into a complete monthly list.

## Status semantics

Distinguish source reachability, transport reachability, search-index availability, freshness, and completeness.

A direct `403`/timeout plus successful indexed recovery is not `DDoSia Monitor = UNAVAILABLE`; it is `direct transport unavailable, indexed source evidence available`.
