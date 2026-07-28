"""Ingest strictly-sourced research JSON (produced by research agents) into the store,
applying no-fabrication gates at the boundary.

Contract: each research file under data/raw/enrichment/*.json is a JSON list of objects
with the fields documented in RESEARCH_SCHEMA below. Every value the agent reports must
carry a source; this ingester enforces the mechanical rules and quarantines violations to
the audit log. Semantic re-verification (re-fetching a cited URL to confirm an email/LinkedIn
actually appears there) happens in pipeline/validation.
"""
from __future__ import annotations
import sys, os, json, re, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.schema import Record, EmailStatus, GENERIC_EMAIL_LOCALPARTS
from pipeline.common import store

ENRICH_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "enrichment")

RESEARCH_SCHEMA = [
    "record_id", "firm_legal_name", "website", "website_source", "domain",
    "fo_type", "fo_type_evidence", "is_fo_evidence", "fo_proof_strength", "family_affiliation",
    "description", "investment_thesis", "investing_sectors", "aum", "aum_basis",
    "corporate_linkedin", "principal_full_name", "principal_title", "principal_relevance",
    "principal_linkedin", "principal_linkedin_status", "principal_email", "email_status",
    "email_source", "email_basis", "principal_phone", "phone_source",
    "signals", "signals_dates", "signals_source", "caveats", "sources_checked",
]

VALID_EMAIL_STATUSES = {e.value for e in EmailStatus}


def _clean_email(rec, obj):
    """No-fabrication gate for email. Returns (email, status, note_for_audit or None)."""
    email = (obj.get("principal_email") or "").strip().lower()
    status = (obj.get("email_status") or "unresolved").strip()
    src = (obj.get("email_source") or "").strip()
    if not email:
        return "", (status if status in VALID_EMAIL_STATUSES else "unresolved"), None
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "", "invalid", f"malformed email '{email}' dropped"
    local = email.split("@")[0]
    if local in GENERIC_EMAIL_LOCALPARTS:
        return "", "unresolved", f"generic mailbox '{email}' is not an individual contact"
    if status not in VALID_EMAIL_STATUSES:
        status = "unverified"
    # A claimed email with no source URL and no provider attestation cannot be 'verified'.
    has_url = bool(re.search(r"https?://", src))
    if status == "verified" and not has_url and "provider" not in src.lower():
        status = "unverified"
        # keep the value but downgrade; note it
        return email, status, f"email '{email}' claimed verified without a source URL -> downgraded to unverified"
    return email, status, None


def _clean_linkedin(url, kind):
    """kind='in' (individual) or 'company'. Returns (url, ok)."""
    u = (url or "").strip()
    if not u:
        return "", False
    if kind == "in" and "/in/" not in u:
        return "", False
    if kind == "company" and "/company/" not in u:
        return "", False
    return u, True


def ingest():
    files = glob.glob(os.path.join(ENRICH_DIR, "*.json"))
    print(f"Ingesting {len(files)} research file(s)...")
    n = 0
    for fp in files:
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            print(f"  SKIP {fp}: {e}"); continue
        if isinstance(data, dict):
            data = [data]
        for obj in data:
            # coerce list-valued fields (some agents return arrays) to strings
            for k, v in list(obj.items()):
                if isinstance(v, list):
                    obj[k] = "; ".join(str(x) for x in v)
            rid = obj.get("record_id", "")
            firm = obj.get("firm_legal_name", rid)
            # find existing candidate by record_id
            existing = [r for r in store.all_candidates() if r["record_id"] == rid]
            key = existing[0]["dedup_key"] if existing else None

            email, estatus, enote = _clean_email(obj, obj)
            if enote:
                store.audit(key or rid, firm, "principal_email",
                            obj.get("principal_email", ""), enote)
            li_person, ok_p = _clean_linkedin(obj.get("principal_linkedin"), "in")
            if obj.get("principal_linkedin") and not ok_p:
                store.audit(key or rid, firm, "principal_linkedin",
                            obj.get("principal_linkedin", ""), "not an individual /in/ profile")
            li_co, _ = _clean_linkedin(obj.get("corporate_linkedin"), "company")

            li_status = obj.get("principal_linkedin_status", "unresolved")
            if not li_person:
                li_status = "unresolved" if li_status != "confirmed" else "unconfirmed"

            rec = Record(
                record_id=rid,
                firm_legal_name=obj.get("firm_legal_name") or obj.get("legal_name", ""),
                firm_common_name=obj.get("firm_common_name", ""),
                # discovery fields (populated when a research agent DISCOVERS a new firm)
                discovery_source_class=obj.get("discovery_source_class", ""),
                discovery_source_detail=obj.get("discovery_source_detail", ""),
                discovery_url=obj.get("discovery_url", ""),
                hq_city=obj.get("hq_city", ""),
                hq_region=obj.get("hq_region", ""),
                hq_country=obj.get("hq_country", ""),
                principal_phone=obj.get("principal_phone", ""),
                phone_source=obj.get("phone_source", ""),
                website=obj.get("website", ""),
                domain=obj.get("domain", ""),
                url_quality=obj.get("url_quality", ""),
                fo_type=obj.get("fo_type", "Undetermined"),
                fo_type_evidence=obj.get("fo_type_evidence", ""),
                is_fo_evidence=obj.get("is_fo_evidence", ""),
                fo_proof_strength=obj.get("fo_proof_strength", ""),
                family_affiliation=obj.get("family_affiliation", ""),
                description=obj.get("description", ""),
                investment_thesis=obj.get("investment_thesis", ""),
                investing_sectors=obj.get("investing_sectors", ""),
                aum=obj.get("aum", ""),
                aum_basis=obj.get("aum_basis", ""),
                corporate_linkedin=li_co,
                principal_full_name=obj.get("principal_full_name", ""),
                principal_title=obj.get("principal_title", ""),
                principal_relevance=obj.get("principal_relevance", ""),
                principal_linkedin=li_person,
                principal_linkedin_status=li_status,
                principal_email=email,
                email_status=estatus,
                email_source=obj.get("email_source", ""),
                email_basis=obj.get("email_basis", ""),
                signals=obj.get("signals", ""),
                signals_dates=obj.get("signals_dates", ""),
                signals_source=obj.get("signals_source", ""),
                caveats=obj.get("caveats", ""),
                last_validated="",
            )
            if store.update_by_record_id(rid, rec) is None:
                store.upsert(rec)  # new firm discovered during enrichment (rare)
            n += 1
    print(f"Ingested {n} enriched records.")


if __name__ == "__main__":
    ingest()
