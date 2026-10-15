"""
Purpose: construct canonical public request URLs for native-web transport fallback across configured live sources.
When used: when a Python source helper cannot reach a host and the same canonical request should be retried through host-native web transport.
Why it exists: preserves source identity and operation semantics across transports while covering the full public-operation surface used by the helpers.
Inputs/parameters: source, operation, optional positional values, and optional structured params for composed filters/limits.
Outputs: JSON containing exact canonical URL plus verified public-page fallback when one exists.
High-level behavior: validates operation-specific values, mirrors helper route construction, and changes only the transport channel.
Failure semantics: unsupported source/operation or invalid input returns a local error; this helper never performs network access.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import urllib.parse
from typing import Any


def encode(value: str, label: str, max_length: int = 300) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > max_length:
        raise ValueError(f"{label} must be 1-{max_length} characters")
    return urllib.parse.quote(cleaned, safe="")


def _limit(params: dict[str, Any] | None, default: int = 100) -> int:
    value = (params or {}).get("limit", default)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be numeric") from exc
    if not 1 <= parsed <= 1000:
        raise ValueError("limit must be 1-1000")
    return parsed


def manifest(
    source: str,
    operation: str,
    value: str | None = None,
    value2: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = params or {}
    alternate_url = None
    alternate_mode = None

    if source == "ransomware.live":
        base = "https://api.ransomware.live/v2"
        if operation == "recent":
            url = f"{base}/recentvictims"
        elif operation == "groups":
            url = f"{base}/groups"
        elif operation == "group":
            url = f"{base}/group/{encode(value or '', 'group')}"
        elif operation == "group-victims":
            url = f"{base}/groupvictims/{encode(value or '', 'group')}"
        elif operation == "search":
            url = f"{base}/recentvictims"
        elif operation == "month":
            year = encode(value or "", "year", 4)
            month = encode(value2 or "", "month", 2)
            url = f"{base}/victims/{year}/{month}"
        elif operation == "country":
            url = f"{base}/countryvictims/{encode(value or '', 'country', 3)}"
        elif operation == "sector":
            url = f"{base}/sectorvictims/{encode(value or '', 'sector', 200)}"
        else:
            raise ValueError("unsupported ransomware.live operation")

    elif source == "ransomfeed":
        base = "https://api.ransomfeed.it"
        limit = _limit(params)
        if operation == "recent":
            url = f"{base}/offset/{limit}"
        elif operation in {"search", "country", "gang"}:
            labels = {"search": "query", "country": "country", "gang": "gang"}
            url = f"{base}/{operation}/{encode(value or '', labels[operation], 300)}/offset/{limit}"
        elif operation == "year":
            year = encode(value or "", "year", 4)
            url = f"{base}/date/{year}/offset/{limit}"
        elif operation == "combined":
            parts: list[str] = []
            for key, path_key, max_len in (
                ("keyword", "search", 300),
                ("country", "country", 100),
                ("gang", "gang", 100),
            ):
                raw = params.get(key)
                if raw:
                    parts.extend([path_key, encode(str(raw), key, max_len)])
            if params.get("year"):
                parts.extend(["date", encode(str(params["year"]), "year", 4)])
            if not parts:
                raise ValueError("combined requires keyword/country/gang/year params")
            url = f"{base}/" + "/".join(parts) + f"/offset/{limit}"
        else:
            raise ValueError("unsupported Ransomfeed operation")

    elif source == "ransomlook":
        base = "https://www.ransomlook.io"
        if operation == "recent":
            url = f"{base}/api/recent"
            alternate_url, alternate_mode = f"{base}/recent", "public-page"
        elif operation == "groups":
            url = f"{base}/api/groups"
        elif operation == "group":
            url = f"{base}/api/group/{encode(value or '', 'group')}"
        elif operation == "leaks":
            url = f"{base}/api/leaks"
        elif operation == "leak":
            url = f"{base}/api/leaks/{encode(value or '', 'leak_id')}"
        elif operation == "search":
            query = urllib.parse.urlencode({"q": (value or "").strip()})
            if not (value or "").strip():
                raise ValueError("query must not be empty")
            url = f"{base}/api/search/?{query}"
        else:
            raise ValueError("unsupported RansomLook operation")

    elif source == "bleepingcomputer":
        base = "https://www.bleepingcomputer.com"
        mapping = {
            "feed": "/feed/",
            "ransomware-tag": "/tag/ransomware/",
            "security-news": "/news/security/",
        }
        if operation in mapping:
            url = base + mapping[operation]
        elif operation == "search":
            query = urllib.parse.urlencode({"q": (value or "").strip()})
            if not (value or "").strip():
                raise ValueError("query must not be empty")
            url = f"{base}/search/?{query}"
        else:
            raise ValueError("unsupported BleepingComputer operation")
        alternate_url, alternate_mode = f"{base}/tag/ransomware/", "public-page"

    elif source == "cybernews":
        base = "https://cybernews.com"
        mapping = {"security": "/security/", "news": "/news/", "feed": "/feed/"}
        if operation in mapping:
            url = base + mapping[operation]
        elif operation == "search":
            query = urllib.parse.urlencode({"q": (value or "").strip()})
            if not (value or "").strip():
                raise ValueError("query must not be empty")
            url = f"{base}/search/?{query}"
        else:
            raise ValueError("unsupported Cybernews operation")
        alternate_url, alternate_mode = f"{base}/security/", "public-page"

    elif source == "securityaffairs":
        base = "https://securityaffairs.com"
        mapping = {"feed": "/feed", "ransomware-tag": "/tag/ransomware"}
        if operation in mapping:
            url = base + mapping[operation]
        elif operation == "search":
            query = urllib.parse.urlencode({"s": (value or "").strip()})
            if not (value or "").strip():
                raise ValueError("query must not be empty")
            url = f"{base}/?{query}"
        else:
            raise ValueError("unsupported Security Affairs operation")
        alternate_url, alternate_mode = f"{base}/tag/ransomware", "public-page"

    elif source == "ransomfeed-web":
        base = "https://www.ransomfeed.it"
        if operation == "docs":
            url = f"{base}/docs/"
        elif operation == "rql":
            raw = (value or "").strip()
            if not raw or len(raw) > 1000:
                raise ValueError("rql must be 1-1000 characters")
            token = base64.b64encode(raw.encode("utf-8")).decode("ascii")
            url = f"{base}/?" + urllib.parse.urlencode({"page": "search-rql", "q": token})
        else:
            raise ValueError("unsupported Ransomfeed Web operation")

    elif source == "ransomnews":
        base = "https://ransomnews.com"
        if operation == "tracker":
            url = f"{base}/ransomtracker/"
        elif operation == "group":
            slug = encode(value or "", "group", 150).replace("%20", "-").lower()
            url = f"{base}/ransomtracker/group/{slug}/"
        else:
            raise ValueError("unsupported Ransomnews operation")

    elif source == "vulone":
        base = "https://vulone.com"
        if operation == "groups":
            url = f"{base}/ransomware-research"
        elif operation == "group":
            raw = (value or "").strip().lower()
            slug = "".join(ch for ch in raw if ch.isalnum())
            if not slug:
                raise ValueError("group must not be empty")
            url = f"{base}/ransomware/{slug}"
        else:
            raise ValueError("unsupported VULONE operation")

    elif source == "threatvectr":
        base = "https://threatvectr.com"
        if operation != "month":
            raise ValueError("unsupported ThreatVectr operation")
        year = encode(value or "", "year", 4)
        month = encode(value2 or "", "month", 2)
        month_names = {
            "1":"january","2":"february","3":"march","4":"april","5":"may","6":"june",
            "7":"july","8":"august","9":"september","10":"october","11":"november","12":"december",
        }
        normalized_month = str(int(month)) if month.isdigit() else month
        if normalized_month not in month_names:
            raise ValueError("month must be 1-12")
        url = f"{base}/ransomware-tracker/reports/{month_names[normalized_month]}-{year}"

    elif source == "ddosia":
        base = "https://ddosia.rfeed.it"
        if operation == "recent":
            limit = str(params.get("limit", value or "20")).strip()
            if not limit.isdigit() or not 1 <= int(limit) <= 500:
                raise ValueError("limit must be 1-500")
            url = f"{base}/api/recent_targets.php?" + urllib.parse.urlencode({"limit": limit})
        elif operation == "search":
            host = (value or "").strip()
            if not host or len(host) > 253:
                raise ValueError("host must be 1-253 characters")
            url = f"{base}/api/search_host.php?" + urllib.parse.urlencode({"host": host})
        elif operation == "date":
            date = (value or "").strip()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                raise ValueError("date must be YYYY-MM-DD")
            url = f"{base}/api/targets_by_date.php?" + urllib.parse.urlencode({"date": date})
        elif operation == "dates":
            url = f"{base}/api/available_dates.php"
        elif operation == "stats":
            stat_type = (value or "").strip()
            allowed = {"overview","by_year","by_month","by_day","timeseries_monthly","timeseries_daily"}
            if stat_type not in allowed:
                raise ValueError("unsupported statistics type")
            url = f"{base}/api/stats.php?" + urllib.parse.urlencode({"type": stat_type})
        else:
            raise ValueError("unsupported DDoSia operation")
        if operation == "search":
            alternate_url = f"{base}/search.php"
        elif operation in {"date", "dates"}:
            alternate_url = f"{base}/calendar.php"
        else:
            alternate_url = f"{base}/index.php"
        alternate_mode = "public-page"

    elif source == "databreaches":
        base = "https://databreaches.net"
        if operation == "feed":
            url = f"{base}/feed/"
        elif operation == "search":
            org = (value or "").strip()
            if not org:
                raise ValueError("organization must not be empty")
            url = f"{base}/?" + urllib.parse.urlencode({"s": org})
        else:
            raise ValueError("unsupported DataBreaches.net operation")

    elif source == "hibp":
        base = "https://haveibeenpwned.com/api/v3"
        if operation == "breaches":
            url = f"{base}/breaches"
        elif operation == "latest":
            url = f"{base}/latestBreach"
        elif operation == "breach":
            url = f"{base}/breach/{encode(value or '', 'breach name')}"
        else:
            raise ValueError("unsupported HIBP operation")

    elif source == "california-ag":
        base = "https://oag.ca.gov"
        if operation == "list":
            url = f"{base}/privacy/databreach/list"
        elif operation == "search":
            org = (value or "").strip()
            if not org:
                raise ValueError("organization must not be empty")
            url = f"{base}/privacy/databreach/list?" + urllib.parse.urlencode({"field_sb24_org_name_value": org})
        else:
            raise ValueError("unsupported California AG operation")

    elif source == "hhs-ocr":
        if operation != "portal":
            raise ValueError("unsupported HHS OCR operation")
        url = "https://ocrportal.hhs.gov/ocr/breach/breach_report_hip.jsf"

    elif source == "sec-edgar":
        if operation != "filings":
            raise ValueError("unsupported SEC EDGAR operation")
        url = "https://www.sec.gov/edgar/search/"

    else:
        raise ValueError("unsupported source")

    return {
        "ok": True,
        "source": source,
        "operation": operation,
        "url": url,
        "alternate_url": alternate_url,
        "alternate_mode": alternate_mode,
        "method": "GET",
        "transport": "native-web-fallback",
        "allow_redirects": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="request_manifest.py")
    parser.add_argument("source")
    parser.add_argument("operation")
    parser.add_argument("value", nargs="?")
    parser.add_argument("value2", nargs="?")
    parser.add_argument("--params-json")
    args = parser.parse_args()

    try:
        params = json.loads(args.params_json) if args.params_json else None
        if params is not None and not isinstance(params, dict):
            raise ValueError("--params-json must decode to an object")
        payload = manifest(args.source, args.operation, args.value, args.value2, params)
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": {"type": "invalid_input", "message": str(exc)}}, ensure_ascii=False, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
