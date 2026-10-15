"""
Purpose: correlate heterogeneous cyber-event families using isolated, profile-driven rules with evidence gates.
When used: for cross-threat questions such as ransomware↔DDoS, ransomware↔data breach, ransomware↔credential leak, ransomware↔exploit activity, DDoS↔hacktivism campaign, and ransomware↔vulnerability exploitation.
Why it exists: keep cross-threat logic modular and extensible without changing the core Tracker/Trend pipelines, while avoiding weak or causal over-inference.
Inputs/parameters: profile id, left/right event lists, optional temporal tolerance in days, optional explicit alias map.
Outputs: deterministic correlation records with canonical entity, relation type, evidence level, dates/date semantics, delta, confidence, event-cluster ids, and aggregate counts.
High-level behavior: resolve entities conservatively, select semantically appropriate dates, apply profile-specific temporal/evidence gates, classify DIRECT/CONTEXTUAL/REJECTED relationships, cluster duplicates, and separate correlation from causality.
Failure semantics: unsupported profiles or invalid tolerance fail explicitly; missing/weak identity or victim-specific evidence never creates a DIRECT match.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
import unicodedata
from typing import Any, Iterable

DIRECT = "DIRECT"
CONTEXTUAL = "CONTEXTUAL"
REJECTED = "REJECTED"

@dataclass(frozen=True)
class CorrelationProfile:
    profile_id: str
    left_type: str
    right_type: str
    match_keys: tuple[str, ...]
    default_tolerance_days: int
    output_semantics: str
    right_date_priority: tuple[str, ...] = ()
    left_date_priority: tuple[str, ...] = ()
    require_victim_specific_right: bool = False
    allow_campaign_context: bool = False
    allow_actor_boost: bool = False

PROFILES: dict[str, CorrelationProfile] = {
    "ransomware_ddos": CorrelationProfile(
        "ransomware_ddos", "ransomware", "ddos",
        ("victim", "organization", "domain"), 14,
        "temporal co-occurrence / correlated exposure",
        allow_actor_boost=True,
    ),
    "ransomware_data_breach": CorrelationProfile(
        "ransomware_data_breach", "ransomware", "data_breach",
        ("victim", "organization", "domain"), 30,
        "cross-incident temporal co-occurrence",
        allow_actor_boost=True,
    ),
    "ransomware_credential_leak": CorrelationProfile(
        "ransomware_credential_leak", "ransomware", "credential_leak",
        ("victim", "organization", "domain"), 30,
        "credential exposure temporally associated with ransomware",
        right_date_priority=("credential_used_date","credential_published_date","credential_discovered_date","credential_stolen_date","date"),
    ),
    "ransomware_exploit_activity": CorrelationProfile(
        "ransomware_exploit_activity", "ransomware", "exploit_activity",
        ("victim", "organization", "domain"), 21,
        "exploit activity temporally associated with ransomware",
        require_victim_specific_right=True, allow_campaign_context=True, allow_actor_boost=True,
    ),
    "ddos_hacktivism_campaign": CorrelationProfile(
        "ddos_hacktivism_campaign", "ddos", "hacktivism_campaign",
        ("victim", "organization", "domain"), 14,
        "DDoS target temporally associated with hacktivism activity",
        allow_campaign_context=True, allow_actor_boost=True,
    ),
    "ransomware_vulnerability_exploitation": CorrelationProfile(
        "ransomware_vulnerability_exploitation", "ransomware", "vulnerability_exploitation",
        ("victim", "organization", "domain"), 30,
        "vulnerability exploitation temporally associated with ransomware",
        require_victim_specific_right=True, allow_campaign_context=True, allow_actor_boost=True,
    ),
}

ORG_SUFFIXES = {
    "inc","incorporated","ltd","limited","llc","plc","corp","corporation","company","co",
    "spa","srl","srls","snc","gmbh","ag","sa","bv"
}

def _norm_text(value: Any) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    text = re.sub(r"^https?://", "", text)
    if "." in text and "/" in text:
        text = text.split("/", 1)[0]
    text = re.sub(r"^www\.", "", text)
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None

def _org_key(value: Any) -> str | None:
    text = _norm_text(value)
    if not text:
        return None
    parts = text.replace(".", " ").split()
    # collapse dotted legal forms such as S.A. -> s a, S.p.A. -> s p a
    if parts[-2:] == ["s","a"]:
        parts = parts[:-2]
    elif parts[-3:] == ["s","p","a"]:
        parts = parts[:-3]
    elif parts[-3:] == ["s","r","l"]:
        parts = parts[:-3]
    elif parts[-3:] == ["l","l","c"]:
        parts = parts[:-3]
    parts = [p for p in parts if p not in ORG_SUFFIXES]
    return " ".join(parts) or text

def _normalized_alias_map(alias_map: dict[str, str] | None) -> dict[str, str]:
    if not alias_map:
        return {}
    out: dict[str, str] = {}
    for k, v in alias_map.items():
        nk = _org_key(k) or _norm_text(k)
        nv = _org_key(v) or _norm_text(v)
        if nk and nv:
            out[nk] = nv
    return out

def _canonical(value: str, aliases: dict[str, str]) -> str:
    return aliases.get(value, value)

def _parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for item in (text, text[:10]):
        try:
            dt = datetime.fromisoformat(item.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return None

GENERIC_DATE_KEYS = ("date","detected_at","attack_date","claim_date","timestamp","published_at")

def _select_date(event: dict[str, Any], priority: Iterable[str]) -> tuple[datetime | None, str | None]:
    seen: set[str] = set()
    for key in tuple(priority) + GENERIC_DATE_KEYS:
        if key in seen:
            continue
        seen.add(key)
        dt = _parse_date(event.get(key))
        if dt:
            return dt, key
    return None, None

def _entity_candidates(event: dict[str, Any], fields: Iterable[str], aliases: dict[str, str]) -> list[tuple[str,str]]:
    out: list[tuple[str,str]] = []
    for field in fields:
        raw = event.get(field)
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            norm = _org_key(item) if field in {"victim","organization"} else _norm_text(item)
            if norm:
                out.append((field, _canonical(norm, aliases)))
    return out

def _match_entity(left: list[tuple[str,str]], right: list[tuple[str,str]]) -> tuple[str,str,str] | None:
    for lf, lv in left:
        for rf, rv in right:
            if lv == rv:
                return lf, rf, lv
    return None

def _verified_actor_id(event: dict[str, Any]) -> str | None:
    status = str(event.get("actor_identity_status") or "").strip().upper()
    actor_id = str(event.get("canonical_actor_id") or "").strip()
    if status == "RESOLVED_ALIAS" and actor_id:
        return actor_id
    return None


def _operation_type(event: dict[str, Any]) -> str:
    raw = (_norm_text(event.get("threat_operation_type")) or "").replace(" ","_")
    if raw in {"ransomware_encryption","data_extortion","ransomware_or_extortion"}:
        return raw
    if event.get("encryption_confirmed") is True:
        return "ransomware_encryption"
    if event.get("extortion_only") is True:
        return "data_extortion"
    return "ransomware_or_extortion"

def _same_incident_hint(left: dict[str, Any], right: dict[str, Any]) -> bool:
    for key in ("incident_id","case_id","campaign_id"):
        if left.get(key) and right.get(key) and str(left[key]) == str(right[key]):
            return True
    return bool(left.get("same_incident") is True or right.get("same_incident") is True)

def _victim_specific(event: dict[str, Any]) -> bool:
    if any(event.get(k) is True for k in (
        "victim_specific","victim_specific_exploitation","target_specific","direct_victim_evidence"
    )):
        return True
    if any(event.get(k) is True for k in ("campaign_level","actor_level","context_only")):
        return False
    if event.get("domain") or event.get("host"):
        return True
    if (event.get("victim") or event.get("organization")) and any(
        event.get(k) for k in ("cve","vulnerability","exploit","exploit_url","evidence_url")
    ):
        return True
    return False

def _campaign_context(event: dict[str, Any]) -> bool:
    return any(event.get(k) is True for k in ("campaign_level","actor_level","context_only"))

def _source_quality(event: dict[str, Any]) -> float:
    authority = (_norm_text(event.get("authority_class")) or "").replace(" ", "_")
    authority_scores = {
        "primary_disclosure": 1.0,
        "regulatory": 0.95,
        "structured_catalogue": 0.88,
        "specialist_osint": 0.78,
        "general_osint": 0.68,
    }
    if authority in authority_scores:
        return authority_scores[authority]
    raw = event.get("source_quality")
    if isinstance(raw, (int,float)):
        return max(0.0,min(1.0,float(raw)))
    st = _norm_text(event.get("source_type")) or ""
    if st in {"official site","government","company advisory","vendor advisory"}:
        return 1.0
    if st in {"reputable media","security research","tracker"}:
        return 0.8
    return 0.6


def _confidence(delta_days: float, tolerance: int, identity_strength: float,
                evidence_specificity: float, source_quality: float, actor_match: bool) -> tuple[str,float]:
    temporal = max(0.0, 1.0 - delta_days / max(1.0,float(tolerance)))
    score = round(max(0.0,min(1.0,
        0.30*identity_strength + 0.25*temporal + 0.25*evidence_specificity +
        0.15*source_quality + 0.05*(1.0 if actor_match else 0.0)
    )),3)
    return ("high" if score >= 0.80 else "medium" if score >= 0.60 else "low", score)

def _cluster_id(event_type: str, entity: str, date_iso: str, event: dict[str, Any]) -> str:
    explicit = event.get("canonical_event_id") or event.get("event_id")
    if explicit:
        return str(explicit)
    basis = "|".join([
        event_type, entity, date_iso,
        _verified_actor_id(event) or _norm_text(event.get("actor")) or _norm_text(event.get("group")) or "",
        _norm_text(event.get("source")) or "",
    ])
    return hashlib.sha256(basis.encode()).hexdigest()[:16]

def correlate(profile_id: str, left_events: list[dict[str,Any]], right_events: list[dict[str,Any]],
              tolerance_days: int | None = None, alias_map: dict[str,str] | None = None) -> dict[str,Any]:
    profile = PROFILES.get(profile_id)
    if profile is None:
        raise ValueError("unsupported correlation profile")
    tolerance = profile.default_tolerance_days if tolerance_days is None else int(tolerance_days)
    if tolerance < 0 or tolerance > 365:
        raise ValueError("tolerance_days must be between 0 and 365")
    aliases = _normalized_alias_map(alias_map)

    matches, rejected = [], []
    seen_pairs: set[tuple[str,str]] = set()

    for left in left_events:
        ld, lsem = _select_date(left, profile.left_date_priority)
        if not ld:
            continue
        lents = _entity_candidates(left, profile.match_keys, aliases)
        if not lents:
            continue
        for right in right_events:
            rd, rsem = _select_date(right, profile.right_date_priority)
            if not rd:
                continue
            rents = _entity_candidates(right, profile.match_keys, aliases)
            if not rents:
                continue
            matched = _match_entity(lents, rents)
            if not matched:
                continue
            lf, rf, entity = matched
            delta = abs((ld-rd).total_seconds())/86400.0
            if delta > tolerance:
                continue

            identity_strength = 1.0 if "domain" in {lf,rf} else 0.9
            level = DIRECT
            reason = None

            if profile.require_victim_specific_right and not _victim_specific(right):
                if profile.allow_campaign_context and _campaign_context(right):
                    level = CONTEXTUAL
                else:
                    level = REJECTED
                    reason = "victim-specific evidence required"

            if profile.profile_id == "ddos_hacktivism_campaign":
                members = right.get("campaign_targets") or right.get("targets")
                if members:
                    norm_members = set()
                    for m in members:
                        nm = _org_key(m) or _norm_text(m)
                        if nm:
                            norm_members.add(_canonical(nm, aliases))
                    if entity in norm_members:
                        level = DIRECT
                    elif level != REJECTED:
                        level = CONTEXTUAL

            la, ra = _verified_actor_id(left), _verified_actor_id(right)
            actor_match = bool(profile.allow_actor_boost and la and ra and la == ra)
            same_incident = _same_incident_hint(left,right)
            relation_type = "same_incident" if same_incident else ("campaign_context" if level == CONTEXTUAL else "temporal_cooccurrence")

            evidence_specificity = 1.0 if level == DIRECT else 0.55 if level == CONTEXTUAL else 0.0
            conf, score = _confidence(delta,tolerance,identity_strength,evidence_specificity,
                                      min(_source_quality(left),_source_quality(right)),actor_match)

            ldate, rdate = ld.date().isoformat(), rd.date().isoformat()
            lc, rc = _cluster_id(profile.left_type,entity,ldate,left), _cluster_id(profile.right_type,entity,rdate,right)
            if (lc,rc) in seen_pairs:
                continue
            seen_pairs.add((lc,rc))

            rec = {
                "profile": profile.profile_id,
                "entity": entity,
                "matched_fields": [lf,rf],
                "left_type": profile.left_type,
                "right_type": profile.right_type,
                "left_date": ldate,
                "right_date": rdate,
                "left_date_semantics": lsem,
                "right_date_semantics": rsem,
                "delta_days": round(delta,3),
                "tolerance_days": tolerance,
                "relation_level": level,
                "relation_type": relation_type,
                "actor_match": actor_match,
                "confidence": conf,
                "confidence_score": score,
                "left_event_cluster_id": lc,
                "right_event_cluster_id": rc,
                "semantics": profile.output_semantics,
                "ransomware_operation_type": (
                    _operation_type(left) if profile.left_type == "ransomware"
                    else _operation_type(right) if profile.right_type == "ransomware" else None
                ),
                "causality_claimed": False,
            }
            if level == REJECTED:
                rec["rejection_reason"] = reason
                rejected.append(rec)
            else:
                matches.append(rec)

    direct = [m for m in matches if m["relation_level"] == DIRECT]
    contextual = [m for m in matches if m["relation_level"] == CONTEXTUAL]
    entities = sorted({m["entity"] for m in matches})
    return {
        "profile": profile.profile_id,
        "tolerance_days": tolerance,
        "match_count": len(matches),
        "direct_match_count": len(direct),
        "contextual_match_count": len(contextual),
        "rejected_count": len(rejected),
        "unique_entity_count": len(entities),
        "unique_entities": entities,
        "matches": matches,
        "rejected": rejected,
        "causality_claimed": False,
    }

def list_profiles() -> list[dict[str,Any]]:
    return [{
        "profile": p.profile_id,
        "left_type": p.left_type,
        "right_type": p.right_type,
        "default_tolerance_days": p.default_tolerance_days,
        "semantics": p.output_semantics,
        "require_victim_specific_right": p.require_victim_specific_right,
    } for p in PROFILES.values()]
