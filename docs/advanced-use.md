[README](../README.md) · [Worked examples](examples.md) · [Advanced use](advanced-use.md) · [Prompts and commands](prompts-and-commands.md)

# Advanced use

## Force a mode or a source

Your instruction wins over automatic routing. Examples: "Use Trend mode and the historical data only." "Query Ransomfeed and RansomLook only." The coverage gate checks the sources of the threat-family scope that was selected.

## Query the bundled history, offline

```bash
python scripts/historical_query.py claims --country IT --start 2024-01-01 --end 2024-12-31 --group-by quarter
python scripts/historical_query.py claims --group-by sector
python scripts/historical_query.py wallets --family <name>
python scripts/historical_query.py eurepoc --keyword <text> --country <text> --start <YYYY-MM-DD> --end <YYYY-MM-DD>
python scripts/historical_query.py repository --strain <name> --sector <text> --location <text> --start-year 2020 --end-year 2024
```

> **Check country labels.** In `historical_query.py` the `--country` filter is a case-insensitive text match, so a short code can match more than one label. The bundled claims also mix codes and full names. For example, grouping 2025 claims by country returned both `AT` and `Austria`. A check with `--country IT --group-by country` on all years matched `IT` (76), `Italy` (1) and also `Kuwait` and `Switzerland` (1 each), because those names contain the letters "it". Run both forms, group by country to see the labels, and read the result. In `filter_records.py`, `--country` is an exact match on the normalized value.

## When a source is blocked or unreachable

Print the exact request, so that the agent can retry it through another transport:

```bash
python scripts/request_manifest.py ransomware.live month <YYYY> <M>
```

*Real output (shortened):* `{"ok":true,"source":"ransomware.live","operation":"month","url":"https://api.ransomware.live/v2/victims/2026/9", ... "transport":"native-web-fallback", ...}`

Build search-index recovery queries:

```bash
python scripts/search_index_fallback.py ransomware.live victim --victim "Example Corp"
```

*Real output (shortened):* `{"ok":true,"source":"ransomware.live", ... "queries":["site:ransomware.live \"Example Corp\"", ...],"channel":"Search index", ...}`

Diagnose the network. A public DNS resolver is a probe only. It is never used to route requests.

```bash
python scripts/diagnose_source.py ransomware.live month <YYYY> <M>
python scripts/network_diagnostics.py api.ransomware.live --probe-public-dns
```

## See the coverage gate refuse an early finish

The gate reads a JSON ledger from standard input. This ledger has one source only, so the gate reports the gaps and exits with code 3.

```bash
echo '[{"source":"ransomware.live","attempted":true,"state":"OK","attempted_paths":["api"],"available_paths":["api","web_api"],"exhausted":false}]' \
  | python scripts/coverage_gate.py
```

*Real output (shortened):* `{"ok":false,"scope":"ransomware","required_sources":["ransomware.live","Ransomfeed", ...],"gaps":[{"source":"ransomware.live","reason":"safe retrieval paths remain","untried_paths":["web_api"]},{"source":"Ransomfeed","reason":"missing ledger entry"}, ...]}`

## Build the status table from evidence

```bash
echo '[{"source":"ransomware.live","attempted":true,"state":"OK","channel":"API","note":"data acquired","evidence":{"success":true}},
       {"source":"Cybernews","attempted":true,"state":"BLOCKED","channel":"Web","note":"HTTP 403","evidence":{"http_status":403}},
       {"source":"VULONE","attempted":false}]' | python scripts/source_status.py
```

*Real output:*

```json
[{"Source":"ransomware.live","Status":"🟢 OK","Channel":"API","Note":"data acquired"},{"Source":"Cybernews","Status":"🟠 BLOCKED","Channel":"Web","Note":"HTTP 403"}]
```

The third source was not attempted and it is not material to this ledger, so no row is made for it. A state without current-run evidence is rejected.

## Actors, sectors and aggregates

- **Actor identity.** `scripts/actor_identity.py` has `resolve` and `compare` commands that read JSON evidence from standard input. A name with no verified alias stays `UNRESOLVED`. The same name used by different actors becomes `ENTITY_COLLISION`. Labels are never merged by fuzzy matching.
- **Sector enrichment.** The skill looks up a sector on the web only when your request needs it and the record has none. If the evidence is weak or conflicting, the sector stays unknown.
- **Aggregates.** The skill does not add up counts from different trackers. It shows one coherent series, or it shows the sources side by side with the difference.
- **Export.** Ask for JSON output when you want to reuse the results.
