# Usage examples

This page lists prompts and a command catalogue. The worked examples with expected output are in [examples.md](examples.md) ([Italiano](examples.it.md)). The advanced use is in [advanced-use.md](advanced-use.md) ([Italiano](advanced-use.it.md)). The pipeline picture is [docs/assets/pipeline.svg](assets/pipeline.svg).

Names in italics are placeholders. Replace them with your own.

## Suggested prompts from the author

The Italian originals are in [README.it.md](../README.it.md). The expected results are described there too.

1. "Show me the number of ransomware victims in Europe, quarter by quarter, from 2020 to today."
2. "Which sectors were hit most by ransomware in Italy between 2021 and today?"
3. "Which ransomware groups collected the most ransom (in euros) in Europe?" The bundled wallet data are in US dollars and have no country, so the skill states that it cannot limit them to Europe.
4. "Which types of legal response to ransomware attacks were most common in the EU?" The skill answers from EuRepoC and uses its categories.
5. "Compare Europe and Italy (country code IT or Italy) and draw a line chart with both. Use data from 2018, or the oldest you have, and update it with the live sources up to today. Quarterly chart."

## Prompts

### Tracker mode

- "Use $ransomware-tracker to check if *Example Corp* appears in recent ransomware claims."
- "Show the latest victims claimed by the group *ExampleGroup*."
- "Does the domain *example.org* appear in ransomware or breach data?"

### Trend mode

- "Create an infographic of the ransomware attack trend in Europe for the last 6 months."
- "Count ransomware claims per quarter for 2023 and 2024, by country."
- "Rank the most active groups by sector and compare the result with the historical dataset."
- "Show ransomware-linked wallet observations with the USD fields."
- "Show EuRepoC incidents that mention *keyword* for a given country and period."

### DDoS

- "Is *example.org* a recent DDoSia target?"
- "Give DDoSia statistics for a date range."

### Data breaches

- "Check *Example Hospital* against the breach sources."

### Cross-threat correlation

- "Do ransomware claims and data breaches overlap for *Example Corp* within the default window?"
- "Correlate DDoS targets with ransomware victims for the last quarter."

Default windows: ±14 days for ransomware ↔ DDoS and DDoS ↔ hacktivism, ±30 days for ransomware ↔ data breach, credential leak and vulnerability exploitation, ±21 days for ransomware ↔ exploit activity.

## Command catalogue

Every line below was checked against the `--help` text of the script. Run `python scripts/<name>.py --help`, or `python scripts/<name>.py <subcommand> --help`, for the full options.

| Script | Subcommands and options |
|---|---|
| `intent_router.py` | `"<request text>"` |
| `ransomware_live.py` | `recent`, `groups`, `group <name>`, `group-victims`, `month <year> <month>`, `country <code>`, `sector <sector>`, `search <keyword>` |
| `ransomlook.py` | `recent`, `groups`, `leaks`, `group`, `leak`, `search <query>` |
| `ransomfeed.py` | `recent`, `search`, `country`, `gang`, `year`, `combined [--keyword --country --gang --year --limit]` |
| `ransomfeed_web.py` | `rql`, `group`, `country-year`, `sector-year`, `victim <name>` |
| `ransomnews.py` | `tracker`, `group <name>` |
| `vulone.py` | `groups`, `group <name>` |
| `threatvectr.py` | `month <year> <month>` |
| `bleepingcomputer.py` | `ransomware-tag`, `security-news`, `feed`, `search <query>` |
| `cybernews.py` | `security`, `news`, `feed`, `search <query>` |
| `security_affairs.py` | `ransomware-tag`, `feed`, `search <query>` |
| `breach_sources.py` | `<california\|databreaches\|hhs\|hibp\|sec> <operation> [value]`; for example `databreaches search <name>` and `hibp latest` |
| `ddosia.py` | `recent [--limit]`, `search <host>`, `date <date>`, `dates`, `stats {by_day,by_month,by_year,overview,timeseries_daily,timeseries_monthly}` |
| `historical_query.py` | `claims [--victim --group --country --sector --start --end --group-by]`, `wallets [--family]`, `eurepoc [--keyword --country --start --end]`, `repository [--strain --sector --location --start-year --end-year]` |
| `normalize_records.py` | `--source <name>`, JSON on standard input |
| `filter_records.py` | `[--keyword --country --date-from --date-to]`, JSON on standard input |
| `actor_identity.py` | `resolve`, `compare`, JSON on standard input |
| `coverage_gate.py` | JSON ledger on standard input; exit code 0 when complete, 3 when gaps remain, 2 on invalid input |
| `source_status.py` | JSON ledger on standard input |
| `request_manifest.py` | `<source> <operation> [value] [value2] [--params-json]` |
| `search_index_fallback.py` | `<source> <kind> [--victim --group --country --sector --host --date --month --text]` |
| `diagnose_source.py` | `<source> <operation> [value] [value2]` |
| `network_diagnostics.py` | `<hostname>... [--public-resolver --probe-public-dns --timeout]` |

`cross_correlation.py`, `sector_enrichment.py`, `fallback_policy.py` and `replacement_policy.py` are meant to be called by the agent. Read their docstrings for inputs and outputs.
