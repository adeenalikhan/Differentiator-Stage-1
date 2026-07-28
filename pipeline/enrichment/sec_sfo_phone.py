"""Deterministic SFO contact enrichment via 13F signature blocks (no model budget).

Several prized single-family offices file Form 13F. The cover carries a verified firm phone
and the signatory (often the professional investment lead behind the family figurehead —
e.g. Cascade's CIO). We add the phone + surface the signatory as an additional verified
contact, WITHOUT overwriting the identified family principal. Pure SEC data; no fabrication.
"""
from __future__ import annotations
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch_json
from pipeline.common import store
from pipeline.enrichment.sec_13f_traverse import _cover, US_STATES


def _cik_from(rec):
    blob = " ".join([rec.get("is_fo_evidence", ""), rec.get("discovery_source_detail", ""),
                     rec.get("signals_source", ""), json.loads(rec["raw"]).get("discovery_url", "")])
    m = re.search(r"CIK[\s:]*([0-9]{6,10})", blob, re.I)
    return m.group(1).zfill(10) if m else None


def _latest_13f(cik):
    d = fetch_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    recent = (d.get("filings") or {}).get("recent") or {}
    for i, f in enumerate(recent.get("form", [])):
        if f and f.startswith("13F"):
            return recent["accessionNumber"][i], recent["filingDate"][i]
    return None, None


def run():
    sfo = [r for r in store.all_candidates()
           if r.get("status") == "qualified" and r["fo_type"] == "SFO" and not r["principal_phone"]]
    print(f"Attempting 13F phone enrichment for {len(sfo)} SFOs without a phone...")
    added = 0
    for r in sfo:
        cik = _cik_from(r)
        if not cik:
            continue
        try:
            acc, date = _latest_13f(int(cik).__str__() and cik)
            if not acc:
                continue
            cov, url = _cover(int(cik), acc.replace("-", ""))
        except Exception as e:
            store.audit(r["dedup_key"], r["firm_legal_name"], "sfo-13f-phone", "", f"failed: {e}")
            continue
        if not cov.get("sig_phone"):
            continue
        note = (f"13F-HR ({date}) signed by {cov['sig_name']} ({cov['sig_title']}) — a verified "
                f"professional contact at the office in addition to the family principal.")
        fields = dict(principal_phone=cov["sig_phone"],
                      phone_source=f"SEC Form 13F-HR signature block, {url}",
                      caveats=((r.get("caveats") or "") + " " + note).strip())
        # fill HQ if missing
        if not r.get("hq_city") and cov.get("city"):
            st = cov.get("state", "")
            fields["hq_city"] = cov["city"]
            fields["hq_region"] = st if st in US_STATES else ""
        store.set_fields(r["record_id"], **fields)
        added += 1
        print(f"  + {r['firm_common_name'][:34]:34} -> {cov['sig_phone']}  (sig: {cov['sig_name']}, {cov['sig_title']})")
    print(f"Added verified firm phones to {added} SFOs from their 13F filings.")


if __name__ == "__main__":
    run()
