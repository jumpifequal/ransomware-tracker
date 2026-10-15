"""
Purpose: query and aggregate the bundled historical ransomware knowledge base using a canonical schema.
When used: in TREND mode for time-series, country/sector/group comparisons, financial summaries, EuRepoC views, and repository history; optionally in TRACKER mode for older entity lookups.
Why it exists: converts heterogeneous JSON/CSV datasets into reproducible analytics using locally bundled historical data.
Inputs/parameters: subcommand plus optional date, country, group, sector, victim, keyword, and grouping filters.
Outputs: JSON containing normalized matching records or grouped summaries with dataset provenance.
High-level behavior: loads only the required local dataset, normalizes fields, filters case-insensitively, deduplicates claim-like records, and aggregates by requested dimension.
Failure semantics: malformed/missing datasets fail explicitly; missing fields remain null and are never inferred.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DATA_DIR = Path(__file__).resolve().parents[1] / "assets" / "historical"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _date(value: Any) -> str | None:
    raw = _text(value)
    if not raw:
        return None
    raw10 = raw[:10]
    formats = ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%Y/%m/%d")
    for fmt in formats:
        try:
            return datetime.strptime(raw10, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _contains(value: Any, needle: str | None) -> bool:
    return True if not needle else needle.casefold() in _text(value).casefold()


def _load_json(name: str) -> Any:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def iter_claims() -> Iterable[dict[str, Any]]:
    datasets = (
        ("ransom.json", "ransom"),
        ("ransom2.json", "ransom2"),
        ("recent.json", "recent"),
    )
    for filename, provenance in datasets:
        for row in _load_json(filename):
            if provenance == "ransom":
                group = row.get("claim_gang")
                if group is False:
                    group = None
                yield {
                    "victim": row.get("victim") or row.get("title"),
                    "group": group,
                    "date": _date(row.get("date")),
                    "country": row.get("country"),
                    "sector": None,
                    "domain": row.get("domain"),
                    "url": row.get("link") or row.get("url") or row.get("claim_url"),
                    "data_type": "incident-or-claim-record",
                    "date_semantics": "source_date",
                    "source": f"historical:{provenance}",
                    "provenance": [f"historical:{provenance}"],
                }
            elif provenance == "ransom2":
                yield {
                    "victim": row.get("victim"),
                    "group": row.get("gang"),
                    "date": _date(row.get("date")),
                    "country": row.get("country"),
                    "sector": row.get("work_sector"),
                    "domain": row.get("website"),
                    "url": None,
                    "data_type": "victim-record",
                    "date_semantics": "source_date",
                    "source": f"historical:{provenance}",
                    "provenance": [f"historical:{provenance}"],
                }
            else:
                yield {
                    "victim": row.get("victim"),
                    "group": row.get("group"),
                    "date": _date(row.get("attackdate") or row.get("discovered")),
                    "country": row.get("country"),
                    "sector": row.get("activity"),
                    "domain": row.get("domain"),
                    "url": row.get("url") or row.get("claim_url"),
                    "data_type": "claim-record",
                    "date_semantics": "attack_or_discovery_date",
                    "source": f"historical:{provenance}",
                    "provenance": [f"historical:{provenance}"],
                }


def claim_records(
    *,
    victim: str | None = None,
    group: str | None = None,
    country: str | None = None,
    sector: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> list[dict[str, Any]]:
    out = []
    seen: set[tuple[str, str, str]] = set()
    for row in iter_claims():
        d = row.get("date")
        if start and (not d or d < start):
            continue
        if end and (not d or d > end):
            continue
        if not _contains(row.get("victim"), victim):
            continue
        if not _contains(row.get("group"), group):
            continue
        if not _contains(row.get("country"), country):
            continue
        if not _contains(row.get("sector"), sector):
            continue
        key = (
            _text(row.get("victim")).casefold(),
            _text(row.get("group")).casefold(),
            _text(d),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def bucket(date_iso: str | None, group_by: str, row: dict[str, Any]) -> str:
    if group_by in {"group", "country", "sector"}:
        return _text(row.get(group_by)) or "Unknown"
    if not date_iso:
        return "Unknown"
    year, month = date_iso.split("-")[:2]
    if group_by == "year":
        return year
    if group_by == "month":
        return f"{year}-{month}"
    if group_by == "quarter":
        q = (int(month) - 1) // 3 + 1
        return f"{year}-Q{q}"
    raise ValueError(f"unsupported group_by: {group_by}")


def aggregate_claims(records: list[dict[str, Any]], group_by: str) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in records:
        counts[bucket(row.get("date"), group_by, row)] += 1
    return [{"bucket": k, "count": counts[k]} for k in sorted(counts)]


def wallet_summary(family: str | None = None) -> dict[str, Any]:
    rows = _load_json("wallets.json")
    matched = [r for r in rows if _contains(r.get("family"), family)]
    total_balance = sum(float(r.get("balanceUSD") or 0) for r in matched)
    tx_usd = 0.0
    tx_count = 0
    families: Counter[str] = Counter()
    for row in matched:
        families[_text(row.get("family")) or "Unknown"] += 1
        for tx in row.get("transactions") or []:
            tx_count += 1
            tx_usd += float(tx.get("amountUSD") or 0)
    return {
        "records": len(matched),
        "families": [{"family": k, "wallets": v} for k, v in families.most_common()],
        "sum_balanceUSD": total_balance,
        "sum_transaction_amountUSD": tx_usd,
        "transactions": tx_count,
        "provenance": ["historical:wallets.json"],
        "data_type": "wallet-observation",
    }


def eurepoc_records(
    keyword: str = "ransom",
    country: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> list[dict[str, Any]]:
    rows = _load_csv("eurepoc_global_dataset_1_3.csv")
    out = []
    for r in rows:
        hay = " ".join([
            _text(r.get("name")),
            _text(r.get("description")),
            _text(r.get("incident_type")),
        ])
        if keyword and keyword.casefold() not in hay.casefold():
            continue
        if country and not (
            _contains(r.get("receiver_country"), country)
            or _contains(r.get("receiver_country_alpha_2_code"), country)
        ):
            continue
        d = _date(r.get("start_date"))
        if start and (not d or d < start):
            continue
        if end and (not d or d > end):
            continue
        out.append({
            "incident_id": r.get("incident_id"),
            "name": r.get("name"),
            "date": d,
            "country": r.get("receiver_country"),
            "country_code": r.get("receiver_country_alpha_2_code"),
            "category": r.get("receiver_category"),
            "incident_type": r.get("incident_type"),
            "attribution_type": r.get("attribution_type"),
            "attribution_basis": r.get("attribution_basis"),
            "source_url": r.get("attribution_source_url"),
            "data_type": "eurepoc-incident",
            "provenance": ["historical:eurepoc_global_dataset_1_3.csv"],
        })
    return out


def repository_records(
    strain: str | None = None,
    sector: str | None = None,
    location: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict[str, Any]]:
    rows = _load_csv("ransomware_repository.csv")
    out = []
    for r in rows:
        year_raw = _text(r.get("Year"))
        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None
        if start_year and (year is None or year < start_year):
            continue
        if end_year and (year is None or year > end_year):
            continue
        if not _contains(r.get("Strain"), strain):
            continue
        if not _contains(r.get("Primary CI Sector targeted"), sector):
            continue
        if not _contains(r.get("Location (State)"), location):
            continue
        out.append({
            "id": r.get("ID Number"),
            "date_began": r.get("Date_Began"),
            "year": year,
            "victim": r.get("OrgName"),
            "location": r.get("Location (State)"),
            "sector": r.get("Primary CI Sector targeted"),
            "group_or_strain": r.get("Strain"),
            "ransom_amount": r.get("Ransom Amount"),
            "currency": r.get("Local Currency"),
            "paid_status": r.get("PaidStatus"),
            "amount_paid": r.get("AmtPaid"),
            "source": r.get("Source"),
            "data_type": "historical-incident-record",
            "provenance": ["historical:ransomware_repository.csv"],
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    claims = sub.add_parser("claims")
    claims.add_argument("--victim")
    claims.add_argument("--group")
    claims.add_argument("--country")
    claims.add_argument("--sector")
    claims.add_argument("--start")
    claims.add_argument("--end")
    claims.add_argument("--group-by", choices=["year", "quarter", "month", "group", "country", "sector"])

    wallets = sub.add_parser("wallets")
    wallets.add_argument("--family")

    legal = sub.add_parser("eurepoc")
    legal.add_argument("--keyword", default="ransom")
    legal.add_argument("--country")
    legal.add_argument("--start")
    legal.add_argument("--end")

    repo = sub.add_parser("repository")
    repo.add_argument("--strain")
    repo.add_argument("--sector")
    repo.add_argument("--location")
    repo.add_argument("--start-year", type=int)
    repo.add_argument("--end-year", type=int)

    args = parser.parse_args()
    if args.mode == "claims":
        records = claim_records(
            victim=args.victim, group=args.group, country=args.country, sector=args.sector,
            start=args.start, end=args.end,
        )
        data = aggregate_claims(records, args.group_by) if args.group_by else records
        result = {"ok": True, "mode": "claims", "count": len(records), "data": data}
    elif args.mode == "wallets":
        result = {"ok": True, "mode": "wallets", "data": wallet_summary(args.family)}
    elif args.mode == "eurepoc":
        data = eurepoc_records(args.keyword, args.country, args.start, args.end)
        result = {"ok": True, "mode": "eurepoc", "count": len(data), "data": data}
    else:
        data = repository_records(args.strain, args.sector, args.location, args.start_year, args.end_year)
        result = {"ok": True, "mode": "repository", "count": len(data), "data": data}

    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
