[README](../README.md) · [Worked examples](examples.md) · [Advanced use](advanced-use.md) · [Prompts and commands](prompts-and-commands.md)

# Worked examples

Each example shows the request, what the skill does behind the scenes, the commands it can run, and the expected output. Run commands from the repository root. Outputs marked *real* were produced by the scripts. Names, numbers and tables marked *example* are placeholders, not real incidents.

## Example 1 · Check one organization (Tracker)

**Ask:** "Use $ransomware-tracker to check if *Example Corp* appears in recent ransomware claims."

**What happens**

1. The router picks Tracker mode and the ransomware scope.

   ```bash
   python scripts/intent_router.py "is Example Corp listed in recent ransomware claims"
   ```

   *Real output (shortened):* `{"mode":"TRACKER", ... "threat_scope":"RANSOMWARE", ...}`

2. The agent asks every API and OSINT source. A few of the commands:

   ```bash
   python scripts/ransomware_live.py search "Example Corp"
   python scripts/ransomlook.py search "Example Corp"
   python scripts/ransomfeed.py combined --keyword "Example Corp" --limit 100
   python scripts/bleepingcomputer.py search "Example Corp"
   python scripts/cybernews.py search "Example Corp"
   python scripts/security_affairs.py search "Example Corp"
   ```

3. Records are normalized to one schema, filtered and de-duplicated (see Example 2).
4. The coverage gate checks that every relevant source was attempted. If one was not, the run continues.
5. The agent writes the answer.

**Expected output (example):**

| Vendor Name | Ransomware Group | Date Published | Link |
|---|---|---|---|
| *Example Corp* | *ExampleGroup* | *2026-09-03* | *https://example.invalid/record* |

The answer ends with the source-status table (see the dashboard below). If no source matches, the skill says **No verified match found**. If a relevant source was blocked or unavailable, it says **Indeterminate / incomplete coverage** instead.

## Example 2 · Infographic: ransomware trend in Europe, last 6 months (Trend)

**Ask:** "Create an infographic of the ransomware attack trend in Europe for the last 6 months."

**What happens**

1. The router picks Trend mode.

   ```bash
   python scripts/intent_router.py "create an infographic of ransomware attack trends in Europe for the last 6 months"
   ```

   *Real output (shortened):* `{"mode":"TREND", ... "threat_scope":"RANSOMWARE", "reason":"aggregation/historical/financial/legal intent"}`

2. The agent collects live data month by month and country by country. "Europe" is a set of country codes that the agent chooses and states.

   ```bash
   python scripts/ransomware_live.py month <YYYY> <M>          # repeat for each of the 6 months
   python scripts/ransomware_live.py country <CC>              # repeat for each country code in the set
   python scripts/ransomfeed.py combined --country <CC> --year <YYYY> --limit 200
   python scripts/threatvectr.py month <YYYY> <M>              # aggregate sanity check only
   ```

3. The agent adds a baseline from the bundled history. The bundled claims in v7 end in 2025, so the recent months must come from live sources.

   ```bash
   python scripts/historical_query.py claims --group-by year
   ```

   *Real output:* `{"ok":true,"mode":"claims","count":3079,"data":[{"bucket":"2021","count":7},{"bucket":"2022","count":22},{"bucket":"2023","count":872},{"bucket":"2024","count":1118},{"bucket":"2025","count":1060}]}`

4. Each live answer is normalized and filtered. The two scripts read JSON from standard input, so they chain with pipes.

   ```bash
   python scripts/ransomware_live.py month <YYYY> <M> \
     | python scripts/normalize_records.py --source ransomware.live \
     | python scripts/filter_records.py --country <CC> --date-from <YYYY-MM-DD> --date-to <YYYY-MM-DD>
   ```

   *Real output for a placeholder record (shortened):* `{"ok":true,"count":1,"records":[{"victim":"Example Corp","group":"examplegroup","date":"2026-09-03 10:00:00","date_semantics":"discovery_date","country":"IT","data_type":"ransomware-claim-record","provenance":["ransomware.live"], ...}],"filters":{...}}`

5. The agent groups by month and country, keeps each tracker's counts apart when they differ, and names the unit it counts (claims, not confirmed attacks).
6. The coverage gate and the status table close the run.

**Expected output:** a short narrative, tables, and a chart or dashboard when your agent can draw one. The picture below shows the layout. **All numbers in it are synthetic.**

![Example final dashboard with synthetic data](assets/example-dashboard.svg)

## Example 3 · Are DDoS and ransomware linked? (cross-threat)

**Ask:** "Do ransomware claims and DDoS targets overlap for *example.org* in the last quarter?"

**What happens**

1. The router sees both threat families and sets the scope to `MIXED`.

   ```bash
   python scripts/intent_router.py "do ransomware and DDoS overlap for example.org"
   ```

   *Real output (shortened):* `{"mode":"TRACKER", ... "threat_scope":"MIXED", ...}`

2. The agent reads the DDoS side from DDoSia Monitor and the ransomware side as in Example 1.

   ```bash
   python scripts/ddosia.py search example.org
   python scripts/ddosia.py recent --limit 50
   python scripts/ddosia.py date <YYYY-MM-DD>
   python scripts/ddosia.py stats overview
   ```

3. The agent correlates the two lists with a profile. The default window for ransomware ↔ DDoS is ±14 days. `cross_correlation.py` is a Python module, so you call it from Python:

   ```bash
   PYTHONPATH=scripts python - <<'PY'
   import cross_correlation as c
   r = c.correlate("ransomware_ddos",
       [{"victim": "Example Corp", "date": "2026-09-01"}],
       [{"organization": "EXAMPLE CORP", "date": "2026-09-09"}])
   m = r["matches"][0]
   print(r["tolerance_days"], r["match_count"], r["direct_match_count"], r["causality_claimed"])
   print(m["relation_type"], m["delta_days"], m["confidence"])
   PY
   ```

   *Real output:*

   ```text
   14 1 1 False
   temporal_cooccurrence 8.0 medium
   ```

**Expected output:** a list of matches with their evidence level (`DIRECT`, `CONTEXTUAL` or `REJECTED`), the date used, the gap in days and the relation type. The skill states that causality is not claimed. Only `DIRECT` matches count in strict incident-level totals.

## Example 4 · Data breach and ransomware together

**Ask:** "Was *Example Hospital* in a data-breach record, and does it match a ransomware claim?"

```bash
python scripts/breach_sources.py databreaches search "Example Hospital"
python scripts/breach_sources.py hibp latest
python scripts/breach_sources.py hibp breaches
```

The other breach sources are `california`, `hhs` and `sec`. The ransomware ↔ data-breach profile (`ransomware_data_breach`) uses a ±30-day window. The skill keeps the incident date, publication date, filing date and catalogue date apart, and it keeps ransomware encryption apart from data extortion.

**Expected output:** a table of matches. Each row shows the source authority class and the meaning of its date.

## Example 5 · Europe against Italy, quarterly line chart

**Ask:** "Compare Europe and Italy (country code IT or Italy) and draw a line chart with both. Use data from 2018, or the oldest you have, and update it with the live sources up to today. Quarterly chart."

**What happens**

1. The router picks Trend mode.
2. The agent looks at the country labels first. The prompt names `IT` and `Italy` on purpose, because the bundled data use both.

   ```bash
   python scripts/historical_query.py claims --country IT --group-by country
   ```

   *Real output:* `{"ok":true,"mode":"claims","count":79,"data":[{"bucket":"IT","count":76},{"bucket":"Italy","count":1},{"bucket":"Kuwait","count":1},{"bucket":"Switzerland","count":1}]}`

   The filter also matched `Kuwait` and `Switzerland`, so the agent keeps only the rows whose label is exactly `IT` or `Italy`.
3. The agent builds the history in two parts, because the bundled data have two different units.

   ```bash
   python scripts/historical_query.py claims --country IT                                            # claims, 2021–2025: records, not grouped
   python scripts/historical_query.py repository --location Italy --start-year 2018 --end-year 2021  # incident repository, 2013–2021
   ```

   The helper matches text, so the agent lists the matching claim records, keeps the exact labels `IT` and `Italy`, and groups them by quarter itself. Using only the name gives a very small series: *real output* of `claims --country Italy --group-by quarter` is one claim (`2025-Q4`), because most Italian claims carry the label `IT`.

   *Real output of the repository command (shortened):* `{"ok":true,"mode":"repository","count":5,"data":[{"id":"622","date_began":"6/1/2020","year":2020, ...}]}`
4. The agent chooses the set of European country codes, states it, and repeats the steps for each code. Then it adds the live months.

   ```bash
   python scripts/ransomware_live.py country <CC>
   python scripts/ransomfeed.py combined --country <CC> --year <YYYY> --limit 200
   ```

5. Live records go through `normalize_records.py` and `filter_records.py` (exact country match), as in Example 2.
6. The coverage gate and the status table close the run.

**Expected output:** a line chart with two lines, Europe and Italy, by quarter. Each segment says where it comes from (repository, claims or live sources) and what it counts. The skill does not join segments with different units into one smooth line without saying so. The chart ends with the source-status table.
