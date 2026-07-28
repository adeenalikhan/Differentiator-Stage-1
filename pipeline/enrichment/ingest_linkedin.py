"""Ingest the SFO LinkedIn-pass output. Updates ONLY principal/LinkedIn/email fields via
set_fields (never a full Record -> no default-clobber of fo_type/proof/etc.). Enforces the
same gates: LinkedIn must be an individual /in/ profile; emails must be non-generic with a
source URL, else quarantined.
"""
from __future__ import annotations
import sys, os, json, glob, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.schema import GENERIC_EMAIL_LOCALPARTS
from pipeline.common import store

ENRICH_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "enrichment")


def ingest():
    files = glob.glob(os.path.join(ENRICH_DIR, "batch_li_*.json"))
    print(f"LinkedIn-pass ingest from {len(files)} file(s)...")
    li_added = princ_updated = email_added = 0
    by_id = {r["record_id"]: r for r in store.all_candidates()}
    for fp in files:
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            print("  SKIP", fp, e); continue
        for o in (data if isinstance(data, list) else [data]):
            rid = o.get("record_id")
            r = by_id.get(rid)
            if not r:
                continue
            fields = {}
            # LinkedIn (individual /in/ only)
            li = (o.get("principal_linkedin") or "").strip()
            if li and "/in/" in li:
                fields["principal_linkedin"] = li
                fields["principal_linkedin_status"] = o.get("principal_linkedin_status") or "confirmed"
                li_added += 1
            elif li:
                store.audit(r["dedup_key"], r["firm_legal_name"], "principal_linkedin", li,
                            "not an individual /in/ profile (LinkedIn pass)")
            # principal name/title update (only if agent supplied a non-empty, changed value)
            nm = (o.get("principal_full_name") or "").strip()
            if nm and nm.lower() != (r.get("principal_full_name") or "").lower():
                fields["principal_full_name"] = nm
                if o.get("principal_title"):
                    fields["principal_title"] = o["principal_title"]
                fields["caveats"] = ((r.get("caveats") or "") + " Principal set to the reachable "
                                     f"investment lead ({nm}) per LinkedIn pass. " + (o.get("note") or "")).strip()
                princ_updated += 1
            # email (rare; gated)
            em = (o.get("principal_email") or "").strip().lower()
            if em and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em) \
               and em.split("@")[0] not in GENERIC_EMAIL_LOCALPARTS \
               and re.search(r"https?://", o.get("email_source") or ""):
                fields["principal_email"] = em
                fields["email_status"] = o.get("email_status") or "unverified"
                fields["email_source"] = o.get("email_source")
                email_added += 1
            if fields:
                store.set_fields(rid, **fields)
    print(f"LinkedIn added={li_added} | principals updated={princ_updated} | emails added={email_added}")


if __name__ == "__main__":
    ingest()
