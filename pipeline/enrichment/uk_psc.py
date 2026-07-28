"""Deterministic UK PSC (Persons with Significant Control) enrichment (no model budget).

The PSC register names who actually controls a UK company. For a single-family office the
controllers are the family. We use it two ways:
  * Always: record the controlling person(s) as evidence (names the family).
  * Qualify as SFO ONLY when the controlling surname matches the firm name AND the SIC is
    genuine investment activity — this separates a real single-family investment office from
    a bare personal-holding shell (cf. the rejected 'Family Office DS').
Corporate PSCs or no-surname-match are left pending for the research pass.
"""
from __future__ import annotations
import sys, os, json, re, html as _html
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch
from pipeline.common import store

BASE = "https://find-and-update.company-information.service.gov.uk/company"
CORP_HINT = re.compile(r"\b(ltd|limited|llp|llc|plc|inc|trustees?|nominees?|holdings|corp)\b", re.I)
STATUS_RE = re.compile(r"\s+(Active|Ceased)\s*$", re.I)


def _pscs(num):
    try:
        html = fetch(f"{BASE}/{num}/persons-with-significant-control", accept="text/html")
    except Exception:
        return []
    out = []
    for raw_h in re.findall(r'<h2[^>]*class="heading-medium[^"]*"[^>]*>(.*?)</h2>', html, re.S):
        txt = _html.unescape(re.sub(r"<[^>]+>", " ", raw_h))
        txt = re.sub(r"\s+", " ", txt).strip()
        active = "Ceased" not in txt
        name = STATUS_RE.sub("", txt).strip()
        if name and "significant control" not in name.lower():
            out.append({"name": name, "active": active, "corporate": bool(CORP_HINT.search(name))})
    return out


def _surname(firm):
    m = re.match(r"(?:the\s+)?([A-Za-z'\-]+)\s+family\s+office", firm.strip(), re.I)
    return m.group(1).lower() if m else ""


def run():
    cands = [r for r in store.all_candidates()
             if r["discovery_source_class"] == "uk-companies-house" and r.get("status") == "pending-enrichment"]
    print(f"PSC-enriching {len(cands)} pending UK candidates...")
    qualified = evidence_only = 0
    for r in cands:
        raw = json.loads(r["raw"])
        num = raw.get("ch_number")
        pscs = _pscs(num)
        active = [p for p in pscs if p["active"]]
        raw["psc"] = pscs
        surname = _surname(r["firm_legal_name"])
        indiv = [p for p in active if not p["corporate"]]
        surname_match = surname and any(surname in p["name"].lower() for p in indiv)
        sic_flag = raw.get("sic_flag")
        psc_txt = "; ".join(p["name"] for p in active) or "none listed"

        if surname_match and sic_flag == "fo-relevant-sic" and indiv:
            fam = surname.capitalize()
            ev = (f"UK Companies House PSC register lists individual controllers sharing the "
                  f"firm's family name ({psc_txt}); firm carries a fund-management/investment "
                  f"SIC ({raw['sic'][0] if raw.get('sic') else ''}). Single-family control of an "
                  f"investment vehicle = single-family office.")
            store.set_fields(
                r["record_id"],
                fo_type="SFO", fo_type_evidence=ev, is_fo_evidence=ev,
                fo_proof_strength="corroborated",
                family_affiliation=f"{fam} family (controlling PSCs: {psc_txt})",
                caveats=((r.get("caveats") or "") +
                         " SFO corroborated via PSC surname match + investment SIC; principal "
                         "and contact pending research pass.").strip())
            qualified += 1
        else:
            note = f"PSC controllers: {psc_txt}." + (" Corporate PSC / no family-name match — FO status pending." if not surname_match else "")
            store.set_fields(r["record_id"], caveats=((r.get("caveats") or "") + " " + note).strip())
            evidence_only += 1
        store.upsert_raw(r["record_id"], raw)
    print(f"PSC -> qualified SFO={qualified} | evidence-only(pending)={evidence_only}")


if __name__ == "__main__":
    run()
