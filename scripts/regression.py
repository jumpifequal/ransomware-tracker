"""
Purpose: package-level regression validation for the ransomware-tracker Universal skill.
When used: after any structural, endpoint, metadata, reference, icon, or Python change and before packaging.
Why it exists: protects package invariants, current endpoint mappings, code syntax, deterministic tests, and package hygiene.
Inputs/parameters: no external inputs; inspects the containing skill directory.
Outputs: PASS/FAIL lines and exit code 0 on success, 1 on any failure.
High-level behavior: checks required resources, validates critical endpoint strings, compiles every Python file, runs deterministic code tests, and rejects build residue.
Failure semantics: every failed invariant is printed and causes a non-zero exit status.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"

REQUIRED = [
    ROOT / "SKILL.md",
    ROOT / "assets" / "icon.jpg",
    ROOT / "agents" / "openai.yaml",
    ROOT / "references" / "operating-rules.md",
    ROOT / "references" / "source-map.md",
    ROOT / "references" / "breach-intelligence.md",
    ROOT / "references" / "unified-data-model.md",
    ROOT / "references" / "actor-identity.md",
    ROOT / "references" / "python-discipline.md",
    SCRIPTS / "_cli_common.py",
    SCRIPTS / "contracts.py",
    SCRIPTS / "_http_common.py",
    SCRIPTS / "_source_runner.py",
    SCRIPTS / "ransomware_live.py",
    SCRIPTS / "ransomfeed.py",
    SCRIPTS / "ransomlook.py",
    SCRIPTS / "bleepingcomputer.py",
    SCRIPTS / "cybernews.py",
    SCRIPTS / "security_affairs.py",
    SCRIPTS / "normalize_records.py",
    SCRIPTS / "filter_records.py",
    SCRIPTS / "fallback_policy.py",
    SCRIPTS / "request_manifest.py",
    SCRIPTS / "diagnose_source.py",
    SCRIPTS / "source_status.py",
    SCRIPTS / "network_diagnostics.py",
    SCRIPTS / "coverage_gate.py",
    SCRIPTS / "replacement_policy.py",
    SCRIPTS / "threatvectr.py",
    SCRIPTS / "vulone.py",
    SCRIPTS / "ransomnews.py",
    SCRIPTS / "ransomfeed_web.py",
    SCRIPTS / "ddosia.py",
    SCRIPTS / "ddosia_search_fallback.py",
    SCRIPTS / "search_index_fallback.py",
    SCRIPTS / "cross_correlation.py",
    SCRIPTS / "actor_identity.py",
    SCRIPTS / "breach_sources.py",
    TESTS / "test_code.py",
]

FORBIDDEN_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}


def check(condition: bool, label: str, failures: list[str]) -> None:
    print(("PASS " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []

    for path in REQUIRED:
        check(path.exists(), f"required file: {path.relative_to(ROOT)}", failures)

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    check("Author: Enrico Frumento" in skill, "author preserved", failures)
    check("request_manifest.py" in skill, "native web fallback documented", failures)
    check("Mandatory source-status footer" in skill, "mandatory source-status footer", failures)
    check("Source reachability policy" in skill, "source reachability policy", failures)
    check("Anti-overfitting transport policy" in skill, "anti-overfitting transport policy", failures)
    check("Web→API" in skill, "hybrid transport status channel documented", failures)
    check("do not use the obsolete `/searchvictims/{keyword}`" in skill.lower(), "obsolete ransomware.live path explicitly prohibited", failures)
    check("do not use `/v1/victims`" in skill.lower(), "obsolete Ransomfeed v1 path explicitly prohibited", failures)

    source_map = (ROOT / "references" / "source-map.md").read_text(encoding="utf-8")
    check("/search/{term}" in source_map, "current Ransomfeed search documented", failures)
    check("BLOCKED" in source_map, "explicit blocked state documented", failures)
    check("RATE_LIMITED" in source_map, "rate-limit state documented", failures)
    fallback_source = (SCRIPTS / "fallback_policy.py").read_text(encoding="utf-8")
    check('"RATE_LIMITED"' in fallback_source, "rate-limited state preserved in fallback policy", failures)
    check("Verified transport routes" in source_map, "verified public fallback routes", failures)
    check("Transport portability" in source_map, "transport portability documented", failures)
    check("## DDoSia Monitor" in source_map, "DDoSia helper documented", failures)
    check("Search-index fallback" in source_map, "DDoSia search-index fallback documented", failures)
    check("## Global search-index recovery" in source_map, "global search-index recovery documented", failures)
    check((ROOT / "references" / "cross-correlation.md").exists(), "cross-correlation module documented", failures)
    check((ROOT / "references" / "actor-identity.md").exists(), "actor identity documented", failures)

    check((ROOT / "references" / "breach-intelligence.md").exists(), "breach intelligence documented", failures)
    unified_model = (ROOT / "references" / "unified-data-model.md").read_text(encoding="utf-8")
    check("canonical_actor_id" in unified_model and "`date`" in unified_model and "`domain`" in unified_model, "canonical event contract documented", failures)
    contracts_source = (SCRIPTS / "contracts.py").read_text(encoding="utf-8")
    check('"RATE_LIMITED"' in contracts_source and '"NOT_TESTED"' in contracts_source, "source-state contract centralized", failures)
    actor_ref = (ROOT / "references" / "actor-identity.md").read_text(encoding="utf-8")
    check("not a hard-coded actor catalogue" in actor_ref, "actor identity is evidence-driven", failures)
    check("Illustrative examples only" in actor_ref, "actor examples are non-normative", failures)
    cross_ref = (ROOT / "references" / "cross-correlation.md").read_text(encoding="utf-8")
    check("DIRECT" in cross_ref and "CONTEXTUAL" in cross_ref and "REJECTED" in cross_ref, "cross-correlation evidence levels documented", failures)
    check("credential_used_date" in cross_ref, "credential date semantics documented", failures)
    check("ransomware_encryption" in cross_ref and "data_extortion" in cross_ref, "ransomware/extortion taxonomy documented", failures)
    check("/api/search_host.php" in source_map and "/api/stats.php" in source_map, "DDoSia endpoints documented", failures)

    http_source = (SCRIPTS / "_http_common.py").read_text(encoding="utf-8")
    check('"api": {' in http_source and '"rss": {' in http_source and '"html": {' in http_source, "content-specific request profiles", failures)
    live_source = (SCRIPTS / "ransomware_live.py").read_text(encoding="utf-8")
    feed_source = (SCRIPTS / "ransomfeed.py").read_text(encoding="utf-8")
    check("/searchvictims/" not in live_source, "obsolete ransomware.live search endpoint absent", failures)
    check("/recentvictims" in live_source, "ransomware.live recent endpoint present", failures)
    check('return "/v1/victims"' not in feed_source and "f\"/v1/victims" not in feed_source, "obsolete Ransomfeed executable path absent", failures)
    check("/search/" in feed_source and "/offset/" in feed_source, "current Ransomfeed filters present", failures)

    yaml = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    check("./assets/icon.jpg" in yaml, "new icon wired in metadata", failures)

    residue = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.name in FORBIDDEN_DIRS or path.suffix in FORBIDDEN_SUFFIXES
    ]
    check(not residue, "package hygiene", failures)

    python_files = list(SCRIPTS.glob("*.py")) + list(TESTS.glob("*.py"))
    for script in python_files:
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
            syntax_ok = True
        except SyntaxError:
            syntax_ok = False
        check(syntax_ok, f"syntax: {script.relative_to(ROOT)}", failures)

    tests = subprocess.run(
        [sys.executable, "-B", "-S", str(TESTS / "test_code.py")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(tests.stdout, end="")
    check(tests.returncode == 0, "deterministic Python code tests", failures)

    residue_after = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.name in FORBIDDEN_DIRS or path.suffix in FORBIDDEN_SUFFIXES
    ]
    check(not residue_after, "package hygiene after regression", failures)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
