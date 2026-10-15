"""
Purpose: deterministic unit-style tests for all ransomware-tracker Python adapters.
When used: run after any code or endpoint mapping change and before package regression.
Why it exists: validates endpoint construction, source-state semantics, canonical normalization, filtering, deduplication, and fallback decisions without live network access.
Inputs/parameters: no external inputs.
Outputs: PASS/FAIL lines and exit code 0 on success, 1 on failure.
High-level behavior: imports modules directly and executes CLI adapters with local JSON fixtures.
Failure semantics: any failed check is reported and produces a non-zero exit status.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check(condition: bool, label: str, failures: list[str]) -> None:
    print(("PASS " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def run_json_cli(script: str, args: list[str], payload) -> tuple[int, dict]:
    process = subprocess.run(
        [sys.executable, "-B", "-S", str(SCRIPTS / script), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return process.returncode, json.loads(process.stdout)


def main() -> int:
    failures: list[str] = []

    cli = load("_cli_common")

    http_common = load("_http_common")

    check(
        http_common.retry_delay_seconds(429, 0, None, '{"message": "1 per 1 minute"}') == 65,
        "ransomware.live one-minute rate-limit delay",
        failures,
    )
    check(
        http_common.retry_delay_seconds(429, 0, "60", None) == 62,
        "Retry-After honored with safety margin",
        failures,
    )

    check(
        http_common.headers_for("api")["User-Agent"] == "Mozilla/5.0",
        "browser-compatible API User-Agent",
        failures,
    )
    check(
        http_common.headers_for("api")["Accept"] == "application/json, text/plain, */*",
        "API Accept profile",
        failures,
    )
    check(
        "application/rss+xml" in http_common.headers_for("rss")["Accept"],
        "RSS Accept profile",
        failures,
    )
    check(
        "text/html" in http_common.headers_for("html")["Accept"],
        "HTML Accept profile",
        failures,
    )
    check(cli.source_state(False, 403, None) == "BLOCKED", "403 => BLOCKED", failures)
    check(cli.source_state(False, 429, None) == "RATE_LIMITED", "429 => RATE_LIMITED", failures)
    check(cli.source_state(False, 404, None) == "INVALID_RESPONSE", "404 => INVALID_RESPONSE", failures)
    check(cli.source_state(False, 500, None) == "UNAVAILABLE", "500 => UNAVAILABLE", failures)

    ransomware_live = load("ransomware_live")
    parser = ransomware_live.build_parser()
    args = parser.parse_args(["month", "2026", "9"])
    path, query, _ = ransomware_live.build_request(args)
    check(path == "/victims/2026/09" and query is None, "ransomware.live month endpoint", failures)

    args = parser.parse_args(["group-victims", "lockbit5"])
    path, _, _ = ransomware_live.build_request(args)
    check(path == "/groupvictims/lockbit5", "ransomware.live group victims endpoint", failures)


    semantic_empty = ransomware_live.SafeRequestError(
        "http_error",
        "HTTP 404",
        404,
        "No victims found '2026-06'.",
    )
    check(
        ransomware_live._is_semantic_empty_404("month", semantic_empty),
        "ransomware.live semantic month 404 => EMPTY",
        failures,
    )
    generic_404 = ransomware_live.SafeRequestError(
        "http_error",
        "HTTP 404",
        404,
        "<html>route not found</html>",
    )
    check(
        not ransomware_live._is_semantic_empty_404("month", generic_404),
        "ransomware.live generic month 404 remains invalid",
        failures,
    )

    ransomfeed = load("ransomfeed")
    parser = ransomfeed.build_parser()
    args = parser.parse_args(["search", "hospital", "--limit", "20"])
    path, _, _ = ransomfeed.build_request(args)
    check(path == "/search/hospital/offset/20", "Ransomfeed search endpoint", failures)

    args = parser.parse_args([
        "combined",
        "--keyword", "hospital",
        "--country", "USA",
        "--year", "2026",
        "--limit", "50",
    ])
    path, _, _ = ransomfeed.build_request(args)
    check(
        path == "/search/hospital/country/USA/date/2026/offset/50",
        "Ransomfeed composed filters",
        failures,
    )

    ransomlook = load("ransomlook")
    parser = ransomlook.build_parser()
    args = parser.parse_args(["search", "Synnovis"])
    path, query, _ = ransomlook.build_request(args)
    check(path == "/api/search/" and query == {"q": "Synnovis"}, "RansomLook search endpoint", failures)

    raw = {
        "data": [
            {
                "victim": "Example Corp",
                "gang": "Qilin",
                "date": "2026-09-20 12:00:00",
                "country": "Italy",
                "website": "example.com",
            }
        ]
    }
    code, normalized = run_json_cli(
        "normalize_records.py",
        ["--source", "ransomfeed"],
        raw,
    )
    check(code == 0 and normalized["count"] == 1, "record normalization", failures)
    record = normalized["records"][0]
    check(record["group"] == "Qilin" and record["domain"] == "example.com" and record["url"] is None and record["date"] == "2026-09-20 12:00:00", "canonical field normalization", failures)

    records = {
        "records": [
            {
                "victim": "Example Corp",
                "group": "Qilin",
                "date": "2026-09-20 12:00:00",
                "country": "Italy",
                "sector": None,
                "url": "example.com",
                "source": "ransomfeed",
            },
            {
                "victim": "example corp",
                "group": "qilin",
                "date": "2026-09-20",
                "country": "Italy",
                "sector": "Technology",
                "url": None,
                "source": "ransomware.live",
            },
        ]
    }
    code, filtered = run_json_cli(
        "filter_records.py",
        ["--keyword", "example", "--country", "Italy"],
        records,
    )
    check(code == 0 and filtered["count"] == 1, "filter + dedupe count", failures)
    check(
        set(filtered["records"][0]["provenance"]) == {"ransomfeed", "ransomware.live"},
        "canonical cross-source provenance",
        failures,
    )


    request_manifest = load("request_manifest")
    m = request_manifest.manifest("ransomware.live", "recent")
    check(m["url"] == "https://api.ransomware.live/v2/recentvictims", "native fallback ransomware.live URL", failures)
    m = request_manifest.manifest("ransomfeed", "search", "hospital")
    check(m["url"] == "https://api.ransomfeed.it/search/hospital/offset/100", "native fallback Ransomfeed URL", failures)
    m = request_manifest.manifest("ransomlook", "search", "Synnovis")
    check(m["url"].startswith("https://www.ransomlook.io/api/search/?q="), "native fallback RansomLook URL", failures)


    m = request_manifest.manifest("ransomware.live", "month", "2026", "6")
    check(
        m["url"] == "https://api.ransomware.live/v2/victims/2026/6",
        "native fallback ransomware.live month URL",
        failures,
    )
    m = request_manifest.manifest("ransomlook", "recent")
    check(
        m["alternate_url"] == "https://www.ransomlook.io/recent",
        "RansomLook public fallback route",
        failures,
    )
    m = request_manifest.manifest("bleepingcomputer", "feed")
    check(
        m["alternate_url"] == "https://www.bleepingcomputer.com/tag/ransomware/",
        "BleepingComputer public fallback route",
        failures,
    )
    m = request_manifest.manifest("securityaffairs", "feed")
    check(
        m["alternate_url"] == "https://securityaffairs.com/tag/ransomware",
        "Security Affairs public fallback route",
        failures,
    )


    rate_limited_input = [
        {
            "source": "ransomware.live",
            "state": "RATE_LIMITED",
            "data": None,
        }
    ]
    proc = subprocess.run(
        [sys.executable, "-B", "-S", str(SCRIPTS / "fallback_policy.py")],
        input=json.dumps(rate_limited_input),
        capture_output=True,
        text=True,
        timeout=5,
    )
    rate_decision = json.loads(proc.stdout)
    check(proc.returncode == 0, "rate-limited fallback policy execution", failures)
    check(
        rate_decision["aggregate_state"] == "RATE_LIMITED",
        "rate-limited fallback state preserved",
        failures,
    )
    check(
        rate_decision["next_action"] == "RUN_REMAINING_COVERAGE"
        and rate_decision["completion_authority"] == "coverage_gate",
        "rate-limited source continues coverage without early completion",
        failures,
    )



    m = request_manifest.manifest("ransomware.live", "month", "2026", "6")
    check(
        m["url"] == "https://api.ransomware.live/v2/victims/2026/6"
        and m["transport"] == "native-web-fallback",
        "canonical request preserved across transport fallback",
        failures,
    )


    source_status = load("source_status")

    row = source_status.normalize_row({
        "source": "ransomware.live",
        "attempted": False,
        "material_omission": True,
        "state": "NOT_TESTED",
    })
    check(
        row["Status"] == "⚪ NOT TESTED",
        "unqueried material source => NOT_TESTED",
        failures,
    )

    try:
        source_status.normalize_row({
            "source": "RansomLook",
            "attempted": False,
            "material_omission": True,
            "state": "UNAVAILABLE",
        })
        unsupported_unavailable_rejected = False
    except ValueError:
        unsupported_unavailable_rejected = True
    check(
        unsupported_unavailable_rejected,
        "unqueried source cannot become UNAVAILABLE",
        failures,
    )

    row = source_status.normalize_row({
        "source": "ransomware.live",
        "attempted": True,
        "state": "UNAVAILABLE",
        "channel": "API",
        "evidence": {
            "error_type": "gaierror",
            "error_message": "temporary failure in name resolution",
        },
    })
    check(
        row["Status"] == "🔴 UNAVAILABLE",
        "attempted source with DNS evidence => UNAVAILABLE",
        failures,
    )

    row = source_status.normalize_row({
        "source": "RansomLook",
        "attempted": False,
        "material_omission": False,
    })
    check(
        row is None,
        "unqueried non-material source omitted",
        failures,
    )


    network_diag = load("network_diagnostics")
    state = network_diag.classify_runtime(
        [
            {"hostname": "a.example", "ok": False, "error_type": "gaierror"},
            {"hostname": "b.example", "ok": False, "error_type": "gaierror"},
        ],
        {
            "udp53": {"ok": False},
            "tcp53": {"ok": False},
        },
    )
    check(
        state == "RUNTIME_WIDE_DNS_OR_EGRESS_RESTRICTION",
        "multi-domain DNS + public DNS failure => runtime-wide restriction",
        failures,
    )

    state = network_diag.classify_runtime(
        [
            {"hostname": "a.example", "ok": False, "error_type": "gaierror"},
            {"hostname": "b.example", "ok": False, "error_type": "gaierror"},
        ],
        {
            "udp53": {"ok": True},
            "tcp53": {"ok": False},
        },
    )
    check(
        state == "SYSTEM_RESOLVER_FAILURE",
        "public resolver reachable => system resolver failure",
        failures,
    )

    state = network_diag.classify_runtime(
        [
            {"hostname": "a.example", "ok": True, "addresses": ["203.0.113.10"]},
            {"hostname": "b.example", "ok": True, "addresses": ["203.0.113.11"]},
        ]
    )
    check(
        state == "SYSTEM_DNS_OK",
        "all system DNS probes succeed",
        failures,
    )


    coverage_gate = load("coverage_gate")

    complete_ledger = [
        {
            "source": source,
            "attempted": True,
            "state": "OK",
            "available_paths": ["primary"],
            "attempted_paths": ["primary"],
            "exhausted": True,
        }
        for source in coverage_gate.RANSOMWARE_SOURCES
    ]
    coverage = coverage_gate.validate_coverage(complete_ledger)
    check(
        coverage["ok"] is True,
        "all configured sources attempted => coverage complete",
        failures,
    )

    missing_one = complete_ledger[:-1]
    coverage = coverage_gate.validate_coverage(missing_one)
    check(
        coverage["ok"] is False,
        "missing configured source => coverage failure",
        failures,
    )

    untried_path = [dict(item) for item in complete_ledger]
    untried_path[0] = {
        "source": "ransomware.live",
        "attempted": True,
        "state": "UNAVAILABLE",
        "available_paths": ["python", "web-api"],
        "attempted_paths": ["python"],
        "exhausted": False,
    }
    coverage = coverage_gate.validate_coverage(untried_path)
    check(
        coverage["ok"] is False,
        "untried safe path => max-effort coverage failure",
        failures,
    )

    exhausted_failure = [dict(item) for item in complete_ledger]
    exhausted_failure[0] = {
        "source": "ransomware.live",
        "attempted": True,
        "state": "UNAVAILABLE",
        "available_paths": ["python", "web-api"],
        "attempted_paths": ["python", "web-api"],
        "exhausted": True,
    }
    coverage = coverage_gate.validate_coverage(exhausted_failure)
    check(
        coverage["ok"] is True,
        "all safe paths exhausted => max-effort completion allowed",
        failures,
    )


    ransomfeed_web = load("ransomfeed_web")
    args = type("Args", (), {"operation": "country-year", "country": "Italy", "year": 2026})()
    path, query, meta = ransomfeed_web.build_request(args)
    check(
        path == "/" and query["page"] == "search-rql" and "country:" in meta["rql"],
        "Ransomfeed Web/RQL structured fallback",
        failures,
    )

    ransomnews = load("ransomnews")
    args = type("Args", (), {"operation": "group", "group": "The Gentlemen"})()
    path, _, meta = ransomnews.build_request(args)
    check(
        path == "/ransomtracker/group/the-gentlemen/"
        and meta["independence"] == "unknown-possible-overlap",
        "Ransomnews group replacement path + lineage",
        failures,
    )

    vulone = load("vulone")
    args = type("Args", (), {"operation": "group", "group": "Qilin"})()
    path, _, meta = vulone.build_request(args)
    check(
        path == "/ransomware/qilin"
        and meta["independence"] == "partial-cross-check-lineage",
        "VULONE tertiary path + lineage",
        failures,
    )

    threatvectr = load("threatvectr")
    args = type("Args", (), {"operation": "month", "year": 2026, "month": 6})()
    path, _, meta = threatvectr.build_request(args)
    check(
        path == "/ransomware-tracker/reports/june-2026"
        and meta["victim_level"] is False,
        "ThreatVectr aggregate-only monthly path",
        failures,
    )

    replacement = load("replacement_policy")
    ladder = replacement.fallback_ladder("ransomware.live")
    check(
        ladder[0] == "ransomware.live:python-api"
        and "Ransomnews/Ransomtracker" in ladder
        and ladder[-1] == "ThreatVectr",
        "ransomware.live replacement ladder",
        failures,
    )

    q = replacement.qualify(
        "Ransomnews/Ransomtracker",
        "victim-record",
        reachable=True,
        content_acquired=True,
        fresh_enough=True,
        has_identity_fields=True,
        history_sufficient=True,
        reproducible_lookup=True,
        sample_coherence=True,
        provenance_declared=True,
    )
    check(
        q["qualified"] is True and q["independence"] == "uncertain-overlap",
        "replacement qualification + overlap disclosure",
        failures,
    )

    q = replacement.qualify(
        "ThreatVectr",
        "victim-record",
        reachable=True,
        content_acquired=True,
        fresh_enough=True,
        has_identity_fields=True,
        history_sufficient=True,
        reproducible_lookup=True,
        sample_coherence=True,
        provenance_declared=True,
    )
    check(
        q["qualified"] is False,
        "aggregate-only source rejected as victim-level replacement",
        failures,
    )

    q = replacement.qualify(
        "VULONE",
        "victim-record",
        reachable=True,
        content_acquired=True,
        fresh_enough=False,
        has_identity_fields=True,
        history_sufficient=True,
        reproducible_lookup=True,
        sample_coherence=True,
        provenance_declared=True,
    )
    check(
        q["qualified"] is False,
        "reachable but stale replacement rejected",
        failures,
    )

    manifest = load("request_manifest")
    check(
        manifest.manifest("ransomnews", "group", "The Gentlemen")["url"].endswith(
            "/ransomtracker/group/the-gentlemen/"
        ),
        "native fallback Ransomnews group URL",
        failures,
    )
    check(
        "search-rql" in manifest.manifest(
            "ransomfeed-web", "rql", "country:Italy"
        )["url"],
        "native fallback Ransomfeed Web/RQL URL",
        failures,
    )
    check(
        manifest.manifest("vulone", "group", "Qilin")["url"].endswith("/ransomware/qilin"),
        "native fallback VULONE group URL",
        failures,
    )
    check(
        manifest.manifest("threatvectr", "month", "2026", "6")["url"].endswith(
            "/ransomware-tracker/reports/june-2026"
        ),
        "native fallback ThreatVectr month URL",
        failures,
    )


    intent_router = load("intent_router")
    check(
        intent_router.route("Mostrami il trend mensile delle vittime in Italia nel 2024")["mode"] == "TREND",
        "intent router trend request",
        failures,
    )
    check(
        intent_router.route("Verifica se ACME compare tra le vittime recenti")["mode"] == "TRACKER",
        "intent router tracker request",
        failures,
    )

    historical = load("historical_query")
    old_claims = historical.claim_records(start="2021-01-01", end="2024-12-31")
    check(
        len(old_claims) > 0,
        "historical claims available",
        failures,
    )
    monthly = historical.aggregate_claims(old_claims, "year")
    check(
        len(monthly) > 0 and "bucket" in monthly[0] and "count" in monthly[0],
        "historical generic aggregation",
        failures,
    )
    wallets = historical.wallet_summary("Netwalker")
    check(
        wallets["records"] > 0 and wallets["data_type"] == "wallet-observation",
        "historical wallet summary",
        failures,
    )
    legal = historical.eurepoc_records(keyword="ransom", start="2020-01-01")
    check(
        isinstance(legal, list),
        "EuRepoC historical query",
        failures,
    )


    sector_enrichment = load("sector_enrichment")
    check(
        sector_enrichment.needs_sector_enrichment(
            None, request_requires_sector=True, victim_name="Mario Rossi"
        ) is True,
        "missing sector + sector-dependent request triggers enrichment",
        failures,
    )
    check(
        sector_enrichment.needs_sector_enrichment(
            None, request_requires_sector=False, victim_name="Mario Rossi"
        ) is False,
        "missing sector without sector-dependent request skips enrichment",
        failures,
    )
    decision = sector_enrichment.evaluate_evidence(
        [{
            "sector": "Healthcare",
            "source_url": "https://example.org/profile",
            "source_type": "employer-site",
            "identity_match": True,
            "person_disambiguated": True,
            "explicit_sector": True,
            "public_source": True,
        }],
        natural_person=True,
    )
    check(
        decision.sector == "Healthcare" and decision.confidence == "high",
        "natural-person sector enrichment requires disambiguated explicit evidence",
        failures,
    )
    decision = sector_enrichment.evaluate_evidence(
        [{
            "sector": "Finance",
            "source_url": "https://example.org/a",
            "source_type": "reputable-media",
            "identity_match": True,
            "person_disambiguated": False,
            "explicit_sector": True,
            "public_source": True,
        }],
        natural_person=True,
    )
    check(
        decision.sector is None,
        "ambiguous person match rejected",
        failures,
    )
    decision = sector_enrichment.evaluate_evidence(
        [
            {
                "sector": "Healthcare",
                "source_url": "https://example.org/a",
                "source_type": "reputable-media",
                "identity_match": True,
                "person_disambiguated": True,
                "explicit_sector": True,
                "public_source": True,
            },
            {
                "sector": "Finance",
                "source_url": "https://example.org/b",
                "source_type": "industry-directory",
                "identity_match": True,
                "person_disambiguated": True,
                "explicit_sector": True,
                "public_source": True,
            },
        ],
        natural_person=True,
    )
    check(
        decision.sector is None and decision.confidence == "conflict",
        "conflicting sector evidence remains unresolved",
        failures,
    )


    ddosia = load("ddosia")
    parser = ddosia.build_parser()

    args = parser.parse_args(["recent", "--limit", "25"])
    path, query, meta = ddosia.build_request(args)
    check(
        path == "/api/recent_targets.php"
        and query == {"limit": 25}
        and meta["data_type"] == "ddosia-target-observation",
        "DDoSia recent-target endpoint",
        failures,
    )

    args = parser.parse_args(["search", "example.com"])
    path, query, _ = ddosia.build_request(args)
    check(
        path == "/api/search_host.php" and query == {"host": "example.com"},
        "DDoSia host-search endpoint",
        failures,
    )

    args = parser.parse_args(["date", "2026-10-06"])
    path, query, _ = ddosia.build_request(args)
    check(
        path == "/api/targets_by_date.php" and query == {"date": "2026-10-06"},
        "DDoSia date endpoint",
        failures,
    )

    args = parser.parse_args(["stats", "timeseries_monthly"])
    path, query, meta = ddosia.build_request(args)
    check(
        path == "/api/stats.php"
        and query == {"type": "timeseries_monthly"}
        and meta["data_type"] == "ddosia-aggregate-statistics",
        "DDoSia statistics endpoint",
        failures,
    )

    m = request_manifest.manifest("ddosia", "search", "example.com")
    check(
        m["url"] == "https://ddosia.rfeed.it/api/search_host.php?host=example.com"
        and m["alternate_url"] == "https://ddosia.rfeed.it/search.php",
        "DDoSia native-web and public-page fallback",
        failures,
    )

    router = load("intent_router")
    ddos_route = router.route("Verifica se example.com compare tra i target DDoS di NoName057")
    check(
        ddos_route["mode"] == "TRACKER" and ddos_route["threat_scope"] == "DDOS",
        "intent router DDoS tracker scope",
        failures,
    )

    ddos_trend_route = router.route("Trend mensile DDoSia negli ultimi mesi")
    check(
        ddos_trend_route["mode"] == "TREND" and ddos_trend_route["threat_scope"] == "DDOS",
        "intent router DDoS trend scope",
        failures,
    )

    coverage_gate = load("coverage_gate")
    ddos_ledger = [{
        "source": "DDoSia Monitor",
        "attempted": True,
        "state": "OK",
        "available_paths": ["api"],
        "attempted_paths": ["api"],
        "exhausted": True,
    }]
    coverage = coverage_gate.validate_coverage(ddos_ledger, scope="ddos")
    check(
        coverage["ok"] is True and coverage["required_sources"] == ["DDoSia Monitor"],
        "DDoS-only coverage gate",
        failures,
    )


    ddosia_search = load("ddosia_search_fallback")
    search_plan = ddosia_search.build_queries(
        "country-month", country="Italia", month="2026-10"
    )
    check(
        search_plan["channel"] == "Search index"
        and any("site:ddosia.rfeed.it" in q for q in search_plan["queries"])
        and any('"2026-10"' in q for q in search_plan["queries"]),
        "DDoSia search-index country-month fallback",
        failures,
    )
    host_search_plan = ddosia_search.build_queries("host", host="example.com")
    check(
        any("search.php" in q and "example.com" in q for q in host_search_plan["queries"]),
        "DDoSia search-index host fallback",
        failures,
    )


    search_index = load("search_index_fallback")

    plan = search_index.build_queries(
        "ransomlook", "victim", victim="ACME"
    )
    check(
        plan["source"] == "RansomLook"
        and plan["channel"] == "Search index"
        and any("site:ransomlook.io" in q and "ACME" in q for q in plan["queries"]),
        "global search-index RansomLook victim fallback",
        failures,
    )

    plan = search_index.build_queries(
        "security affairs", "text", text="Italy DDoS October 2026"
    )
    check(
        plan["policy"]["editorial_source"] is True
        and any("site:securityaffairs.com" in q for q in plan["queries"]),
        "global search-index editorial fallback",
        failures,
    )

    plan = search_index.build_queries(
        "threatvectr", "month", month="2026-10"
    )
    check(
        plan["policy"]["aggregate_only"] is True
        and plan["semantic_unit"] == "ransomware aggregate statistic",
        "global search-index aggregate-only semantics",
        failures,
    )

    plan = search_index.build_queries(
        "ddosia", "recent"
    )
    check(
        plan["semantic_unit"] == "DDoS target observation"
        and any("ddosia.rfeed.it" in q for q in plan["queries"]),
        "global search-index DDoS semantics",
        failures,
    )


    cross = load("cross_correlation")
    profile_ids = {item["profile"] for item in cross.list_profiles()}
    check(
        {
            "ransomware_ddos",
            "ransomware_data_breach",
            "ransomware_credential_leak",
            "ransomware_exploit_activity",
            "ddos_hacktivism_campaign",
            "ransomware_vulnerability_exploitation",
        }.issubset(profile_ids),
        "cross-correlation profiles available",
        failures,
    )

    corr = cross.correlate(
        "ransomware_ddos",
        [{"victim": "Comune di Bari", "date": "2026-10-01"}],
        [{"organization": "COMUNE DI BARI", "date": "2026-10-10"}],
    )
    check(
        corr["unique_entity_count"] == 1
        and corr["match_count"] == 1
        and corr["matches"][0]["delta_days"] == 9
        and corr["tolerance_days"] == 14
        and corr["causality_claimed"] is False,
        "ransomware-DDoS default ±14-day correlation",
        failures,
    )

    no_corr = cross.correlate(
        "ransomware_ddos",
        [{"victim": "Example Corp", "date": "2026-01-01"}],
        [{"victim": "Example Corp", "date": "2026-02-01"}],
    )
    check(
        no_corr["match_count"] == 0,
        "ransomware-DDoS rejects out-of-window matches",
        failures,
    )

    domain_corr = cross.correlate(
        "ransomware_vulnerability_exploitation",
        [{"domain": "https://www.example.com", "date": "2026-03-10"}],
        [{"domain": "example.com", "date": "2026-03-20"}],
    )
    check(
        domain_corr["match_count"] == 1,
        "cross-correlation domain normalization",
        failures,
    )


    hard = cross.correlate(
        "ransomware_credential_leak",
        [{"victim": "Efficy S.A.", "claim_date": "2026-02-16"}],
        [{"organization": "Efficy", "credential_used_date": "2026-03-05"}],
    )
    check(
        hard["direct_match_count"] == 1
        and hard["matches"][0]["right_date_semantics"] == "credential_used_date",
        "credential date semantics + direct correlation",
        failures,
    )

    contextual = cross.correlate(
        "ransomware_vulnerability_exploitation",
        [{"victim": "Example Corp", "date": "2026-04-01"}],
        [{"organization": "Example Corp", "date": "2026-04-03", "campaign_level": True}],
    )
    check(
        contextual["direct_match_count"] == 0
        and contextual["contextual_match_count"] == 1
        and contextual["matches"][0]["relation_type"] == "campaign_context",
        "victim-specific evidence gate",
        failures,
    )

    rejected = cross.correlate(
        "ransomware_vulnerability_exploitation",
        [{"victim": "Example Corp", "date": "2026-04-01"}],
        [{"organization": "Example Corp", "date": "2026-04-03"}],
    )
    check(
        rejected["match_count"] == 0 and rejected["rejected_count"] == 1,
        "weak vulnerability correlation rejected",
        failures,
    )

    same_incident = cross.correlate(
        "ransomware_data_breach",
        [{"victim": "Lovesac", "date": "2025-03-03", "incident_id": "INC-1"}],
        [{"organization": "Lovesac Inc.", "date": "2025-03-03", "incident_id": "INC-1"}],
    )
    check(
        same_incident["matches"][0]["relation_type"] == "same_incident",
        "same-incident breach classification",
        failures,
    )

    operation = cross.correlate(
        "ransomware_ddos",
        [{"victim": "Acme Ltd.", "date": "2026-01-01", "extortion_only": True}],
        [{"organization": "Acme", "date": "2026-01-02"}],
    )
    check(
        operation["matches"][0]["ransomware_operation_type"] == "data_extortion",
        "ransomware/extortion taxonomy",
        failures,
    )

    alias_match = cross.correlate(
        "ransomware_ddos",
        [{"victim": "Acme Holdings", "date": "2026-01-01"}],
        [{"organization": "Acme Brand", "date": "2026-01-02"}],
        alias_map={"acme holdings": "acme canonical", "acme brand": "acme canonical"},
    )
    check(alias_match["direct_match_count"] == 1, "explicit alias resolution", failures)

    precise = cross.correlate(
        "ransomware_ddos",
        [{"victim": "Time Test", "date": "2026-01-01T23:00:00+00:00"}],
        [{"organization": "Time Test", "date": "2026-01-16T00:30:00+00:00"}],
        tolerance_days=14,
    )
    check(precise["match_count"] == 0, "elapsed-time boundary uses total seconds", failures)


    actor_identity = load("actor_identity")

    actor_records = [
        {
            "actor_id": "actor:ddos-alpha",
            "canonical_name": "Alpha",
            "aliases": ["SharedName", "Alpha-D"],
            "threat_families": ["ddos", "hacktivism"],
            "operation_types": ["ddos"],
            "verified": True,
            "alias_confidence": "HIGH",
        },
        {
            "actor_id": "actor:ransom-beta",
            "canonical_name": "Beta",
            "aliases": ["SharedName", "Beta-R"],
            "threat_families": ["ransomware", "extortion"],
            "operation_types": ["data_extortion"],
            "verified": True,
            "alias_confidence": "HIGH",
        },
        {
            "actor_id": "actor:multi-alias",
            "canonical_name": "Canonical Cluster",
            "aliases": ["Vendor Name A", "Vendor Name B", "Vendor Name C"],
            "threat_families": ["extortion"],
            "operation_types": ["data_extortion"],
            "verified": True,
            "alias_confidence": "HIGH",
        },
        {
            "actor_id": "actor:unverified",
            "canonical_name": "Speculative Cluster",
            "aliases": ["GuessAlias"],
            "threat_families": ["ransomware"],
            "operation_types": ["ransomware_or_extortion"],
            "verified": False,
        },
    ]

    ambiguous = actor_identity.resolve("SharedName", actor_records)
    check(
        ambiguous["status"] == "ENTITY_COLLISION"
        and {c["actor_id"] for c in ambiguous["candidates"]}
        == {"actor:ddos-alpha", "actor:ransom-beta"},
        "generic homonym collision is not merged",
        failures,
    )

    ddos_resolved = actor_identity.resolve("SharedName", actor_records, "ddos")
    check(
        ddos_resolved["status"] == "RESOLVED_ALIAS"
        and ddos_resolved["actor_id"] == "actor:ddos-alpha",
        "family context disambiguates verified collision",
        failures,
    )

    aliases = actor_identity.same_actor(
        "Vendor Name A", "Vendor Name C", actor_records
    )
    check(
        aliases["same_actor"] is True
        and aliases["relation"] == "VERIFIED_ALIAS_SET"
        and aliases["left"]["actor_id"] == "actor:multi-alias",
        "generic verified multi-vendor alias set",
        failures,
    )

    distinct = actor_identity.same_actor(
        "Alpha-D", "Beta-R", actor_records
    )
    check(
        distinct["same_actor"] is False
        and distinct["relation"] == "DISTINCT_ENTITY",
        "generic distinct actors remain separate",
        failures,
    )

    unverified = actor_identity.resolve("GuessAlias", actor_records)
    check(
        unverified["status"] == "UNRESOLVED",
        "unverified alias evidence cannot resolve identity",
        failures,
    )

    mismatch = actor_identity.resolve("Canonical Cluster", actor_records, "ransomware")
    check(
        mismatch["status"] == "FAMILY_MISMATCH"
        and mismatch["merge_allowed"] is False,
        "contradictory family hint is rejected",
        failures,
    )

    contracts = load("contracts")
    check(
        {"OK","EMPTY","BLOCKED","RATE_LIMITED","UNAVAILABLE","INVALID_RESPONSE","NOT_TESTED"}
        == contracts.SOURCE_STATES,
        "canonical contract state vocabulary",
        failures,
    )
    check(
        contracts.classify_source_state(False, 401, None) == "BLOCKED"
        and contracts.classify_source_state(False, 405, None) == "INVALID_RESPONSE",
        "HTTP state classification uses shared contract",
        failures,
    )

    m = request_manifest.manifest("ransomware.live", "country", "IT")
    check(
        m["url"] == "https://api.ransomware.live/v2/countryvictims/IT",
        "native fallback ransomware.live country parity",
        failures,
    )
    m = request_manifest.manifest("ransomware.live", "sector", "Healthcare")
    check(
        m["url"].endswith("/sectorvictims/Healthcare"),
        "native fallback ransomware.live sector parity",
        failures,
    )
    m = request_manifest.manifest("ransomlook", "leak", "abc-123")
    check(
        m["url"].endswith("/api/leaks/abc-123"),
        "native fallback RansomLook leak parity",
        failures,
    )
    m = request_manifest.manifest(
        "ransomfeed", "combined",
        params={"keyword":"hospital","country":"USA","year":2026,"limit":50},
    )
    check(
        m["url"] == "https://api.ransomfeed.it/search/hospital/country/USA/date/2026/offset/50",
        "native fallback Ransomfeed combined parity",
        failures,
    )

    breach_sources = load("breach_sources")
    parser = breach_sources.build_parser()
    args = parser.parse_args(["databreaches", "feed"])
    source, base, path, query, meta, profile = breach_sources.build_request(args)
    check(
        source == "DataBreaches.net" and path == "/feed/" and profile == "rss"
        and meta["authority_class"] == "SPECIALIST_OSINT",
        "DataBreaches.net breach acquisition",
        failures,
    )
    args = parser.parse_args(["hibp", "latest"])
    source, base, path, query, meta, profile = breach_sources.build_request(args)
    check(
        path == "/api/v3/latestBreach" and meta["authority_class"] == "STRUCTURED_CATALOGUE",
        "HIBP breach acquisition",
        failures,
    )
    check(
        "DataBreaches.net" in coverage_gate.required_sources("breach")
        and "ransomware.live" in coverage_gate.required_sources("ransomware_breach"),
        "breach coverage scopes",
        failures,
    )
    breach_route = router.route("correlazione ransomware con data breach")
    check(
        breach_route["threat_scope"] == "RANSOMWARE_BREACH",
        "intent router ransomware-breach scope",
        failures,
    )
    breach_plan = search_index.build_queries("databreaches.net", "victim", victim="Example Corp")
    check(
        any("site:databreaches.net" in q and "data breach" in q for q in breach_plan["queries"]),
        "breach search-index recovery uses breach semantics",
        failures,
    )
    ddos_host_plan = search_index.build_queries("ddosia", "host", host="example.com")
    check(
        all("ransomware" not in q.casefold() for q in ddos_host_plan["queries"]),
        "generic DDoS search-index recovery avoids ransomware wording",
        failures,
    )

    actor_boost = cross.correlate(
        "ransomware_ddos",
        [{
            "victim":"Actor Test","date":"2026-01-01",
            "group":"Alias A","canonical_actor_id":"actor:verified",
            "actor_identity_status":"RESOLVED_ALIAS",
        }],
        [{
            "organization":"Actor Test","date":"2026-01-02",
            "actor":"Alias B","canonical_actor_id":"actor:verified",
            "actor_identity_status":"RESOLVED_ALIAS",
        }],
    )
    check(
        actor_boost["matches"][0]["actor_match"] is True,
        "verified canonical actor id enables actor boost",
        failures,
    )
    raw_only = cross.correlate(
        "ransomware_ddos",
        [{"victim":"Raw Actor","date":"2026-01-01","group":"Same Label"}],
        [{"organization":"Raw Actor","date":"2026-01-02","actor":"Same Label"}],
    )
    check(
        raw_only["matches"][0]["actor_match"] is False,
        "raw actor string equality cannot enable actor boost",
        failures,
    )

    fallback_input = [
        {
            "ok": True,
            "state": "EMPTY",
            "source": "ransomware.live",
            "data": {"results": []},
        },
        {
            "ok": False,
            "state": "BLOCKED",
            "source": "cybernews",
            "data": None,
        },
    ]
    code, fallback = run_json_cli(
        "fallback_policy.py",
        [],
        fallback_input,
    )
    check(code == 0, "fallback policy execution", failures)
    check(fallback["next_action"] == "RUN_REMAINING_COVERAGE" and fallback["completion_authority"] == "coverage_gate", "fallback completion delegated to coverage gate", failures)
    check(fallback["aggregate_state"] == "PARTIAL_FAILURE", "fallback state precision", failures)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
