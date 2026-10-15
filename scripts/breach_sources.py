"""
Purpose: query public data-breach intelligence sources used by breach lookup/trend workflows and ransomware↔data-breach correlation.
When used: whenever the selected threat scope includes BREACH or RANSOMWARE_BREACH.
Why it exists: closes the evidence-ingestion gap between the existing data-breach correlation profile and actual specialist/structured/regulatory/primary source retrieval.
Inputs/parameters: source selector, operation, and optional organization/breach identifier.
Outputs: one standard source envelope with authority_class, date semantics, and semantic data type metadata.
High-level behavior: retrieves stable public RSS/API/web surfaces; blocked direct transport remains eligible for web/search-index recovery.
Failure semantics: transport failure is source-state evidence only and never proves absence of a breach.
"""
from __future__ import annotations

import argparse
from urllib.parse import quote

from _cli_common import print_json, query_text
from _source_runner import execute

SOURCE_CONFIG = {
    "databreaches": ("DataBreaches.net", "https://databreaches.net", "SPECIALIST_OSINT"),
    "hibp": ("Have I Been Pwned", "https://haveibeenpwned.com", "STRUCTURED_CATALOGUE"),
    "california": ("California AG", "https://oag.ca.gov", "REGULATORY"),
    "hhs": ("HHS OCR", "https://ocrportal.hhs.gov", "REGULATORY"),
    "sec": ("SEC EDGAR Item 1.05", "https://www.sec.gov", "PRIMARY_DISCLOSURE"),
}


def build_request(args: argparse.Namespace):
    source, base, authority = SOURCE_CONFIG[args.source]
    query = None
    profile = "html"
    meta = {
        "operation": args.operation,
        "authority_class": authority,
        "data_type": "data-breach-evidence",
    }

    if args.source == "databreaches":
        if args.operation == "feed":
            path, profile = "/feed/", "rss"
            meta["date_semantics"] = "publication_date"
        elif args.operation == "search":
            org = query_text(args.value, "organization", 200)
            path, query = "/", {"s": org}
            meta.update({"organization": org, "date_semantics": "publication_date"})
        else:
            raise ValueError("unsupported DataBreaches.net operation")

    elif args.source == "hibp":
        if args.operation == "breaches":
            path, profile = "/api/v3/breaches", "api"
        elif args.operation == "latest":
            path, profile = "/api/v3/latestBreach", "api"
        elif args.operation == "breach":
            name = query_text(args.value, "breach name", 200)
            path, profile = f"/api/v3/breach/{quote(name, safe='')}", "api"
            meta["breach_name"] = name
        else:
            raise ValueError("unsupported HIBP operation")
        meta["date_semantics"] = ["breach_date", "catalog_added_date"]

    elif args.source == "california":
        path = "/privacy/databreach/list"
        if args.operation == "search":
            org = query_text(args.value, "organization", 200)
            query = {"field_sb24_org_name_value": org}
            meta["organization"] = org
        elif args.operation != "list":
            raise ValueError("unsupported California AG operation")
        meta["date_semantics"] = ["breach_date", "reported_date"]

    elif args.source == "hhs":
        if args.operation != "portal":
            raise ValueError("unsupported HHS OCR operation")
        path = "/ocr/breach/breach_report_hip.jsf"
        meta.update({
            "date_semantics": ["breach_date", "submission_date"],
            "scope_note": "HIPAA breach portal scope applies",
        })

    elif args.source == "sec":
        if args.operation != "filings":
            raise ValueError("unsupported SEC operation")
        path = "/edgar/search/"
        meta.update({
            "date_semantics": ["incident_date", "filing_date"],
            "form": "8-K",
            "item": "1.05",
        })
    else:
        raise ValueError("unsupported source")

    return source, base, path, query, meta, profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="breach_sources.py")
    parser.add_argument("source", choices=sorted(SOURCE_CONFIG))
    parser.add_argument("operation")
    parser.add_argument("value", nargs="?")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        source, base, path, query, meta, profile = build_request(args)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        print_json({
            "ok": False,
            "state": "INVALID_RESPONSE",
            "source": SOURCE_CONFIG.get(getattr(args, "source", ""), (getattr(args, "source", None), "", ""))[0],
            "request": {"operation": getattr(args, "operation", None)},
            "status": None,
            "data": None,
            "error": {"type": "invalid_input", "message": str(exc), "status": None},
        })
        return 2
    return execute(source, base, path, query, meta, profile=profile)


if __name__ == "__main__":
    raise SystemExit(main())
