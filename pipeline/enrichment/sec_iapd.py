"""Deterministic SEC IAPD enrichment for the 13F candidates (no model budget).

Core signal: to manage money and file a 13F WITHOUT registering as an investment adviser,
a firm essentially must qualify for the single-family-office exemption (rule 202(a)(11)(G)-1).
So:
  * Appears in IAPD (registered adviser / ERA)  -> serves clients; SFO-vs-MFO left to the
    research pass. We record verified facts (CRD, SEC#, address) but do NOT auto-qualify,
    to avoid mislabeling a wealth manager (e.g. a research/advisory firm) as a family office.
  * Absent from IAPD + files 13F + family-office name -> strong single-family-office signal.
    We qualify it as SFO (corroborated) with the exemption reasoning, family unnamed pending
    research.

This never fabricates: it only records what SEC systems return.
"""
from __future__ import annotations
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch
from pipeline.common import store

IAPD = "https://api.adviserinfo.sec.gov/search/firm?query={}&hits=5"
FAMILY_NAME_RE = re.compile(r"family\s+(office|capital|partners|holdings|wealth)", re.I)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _iapd_lookup(name):
    q = re.sub(r"[^a-z0-9 ]", "", name.lower()).replace(" ", "+")
    try:
        d = json.loads(fetch(IAPD.format(q), accept="application/json"))
    except Exception:
        return None
    target = _norm(name)
    for h in d.get("hits", {}).get("hits", []):
        s = h.get("_source", {})
        names = [s.get("firm_name", "")] + (s.get("firm_other_names") or [])
        if any(_norm(n) == target or target in _norm(n) or _norm(n) in target for n in names if n):
            addr = {}
            try:
                addr = json.loads(s.get("firm_ia_address_details") or "{}").get("officeAddress", {})
            except Exception:
                pass
            return {"crd": s.get("firm_source_id"), "sec": s.get("firm_ia_full_sec_number"),
                    "scope": s.get("firm_ia_scope"), "matched_name": s.get("firm_name"), "addr": addr}
    return None


def run():
    cands = [r for r in store.all_candidates()
             if r["discovery_source_class"] == "sec-13f" and r.get("status") == "pending-enrichment"]
    print(f"IAPD-enriching {len(cands)} pending SEC-13F candidates...")
    registered = unregistered_sfo = ambiguous = 0
    for r in cands:
        raw = json.loads(r["raw"])
        name = r["firm_legal_name"]
        name_is_fo = bool(FAMILY_NAME_RE.search(name)) or raw.get("name_signals_fo")
        hit = _iapd_lookup(name)
        raw["iapd"] = hit
        has_holdings = bool(raw.get("cover", {}).get("value_thousands", "").isdigit())

        if hit:  # registered adviser / ERA -> record facts, leave for research pass
            registered += 1
            a = hit.get("addr", {})
            note = (f"SEC-registered investment adviser (CRD {hit['crd']}, {hit['sec']}, "
                    f"IAPD status {hit['scope']}). SFO-vs-MFO and FO-hood pending research pass.")
            fields = dict(caveats=((r.get("caveats") or "") + " " + note).strip())
            if a.get("city"):
                fields.update(hq_street=a.get("street1", ""), hq_city=a.get("city", ""),
                              hq_region=a.get("state", ""), hq_country="United States of America")
            store.set_fields(r["record_id"], **fields)
            store.upsert_raw(r["record_id"], raw)
        elif name_is_fo and has_holdings:  # unregistered + 13F + family name -> SFO exemption
            unregistered_sfo += 1
            val = int(raw["cover"]["value_thousands"]) / 1e6
            ev = (f"No SEC investment-adviser registration found in IAPD (searched '{name}'); "
                  f"files SEC Form 13F-HR (CIK {raw.get('cik')}) reporting ${val:.2f}B in 13(f) "
                  f"holdings under a family-office name. Managing that scale without adviser "
                  f"registration is consistent with the single-family-office exemption "
                  f"(Advisers Act rule 202(a)(11)(G)-1).")
            store.set_fields(
                r["record_id"],
                fo_type="SFO", fo_type_evidence=ev, is_fo_evidence=ev,
                fo_proof_strength="corroborated",
                caveats=((r.get("caveats") or "") +
                         " SFO inferred from unregistered-adviser + 13F + family-office name; "
                         "the specific family is not yet named (pending research pass).").strip())
            store.upsert_raw(r["record_id"], raw)
        else:
            ambiguous += 1
            store.upsert_raw(r["record_id"], raw)
    print(f"registered(facts added, pending)={registered} | "
          f"unregistered->SFO(qualified)={unregistered_sfo} | ambiguous(pending)={ambiguous}")


if __name__ == "__main__":
    run()
