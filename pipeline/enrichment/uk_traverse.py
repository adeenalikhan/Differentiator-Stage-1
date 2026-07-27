"""Traverse each UK Companies House candidate's profile + officers page.

Extracts SIC codes (to separate genuine investment/FO activity from property mgmt,
insurance, etc.) and the ACTIVE officers list (directors = principal candidates). Does
NOT auto-assign a principal — UK FOs often use corporate/nominee directors, so the real
decision-maker is chosen later in principal enrichment. Officers + SIC are stored in raw.
"""
from __future__ import annotations
import sys, os, json, re, html as _html
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch
from pipeline.common.schema import Record
from pipeline.common import store

BASE = "https://find-and-update.company-information.service.gov.uk/company"

# SIC codes consistent with an investment/holding/family-office operation.
FO_RELEVANT_SIC = {"64205", "64209", "64301", "64303", "64304", "64305", "64999",
                   "66300", "66190", "70100", "70221", "64991", "64301"}
# SIC codes that argue AGAINST a genuine investment family office.
NON_FO_SIC_PREFIX = ("68",  # real estate
                     "65",  # insurance
                     "69",  # legal/accounting
                     "82",  # business support
                     "47", "56", "55")  # retail/food/hotels


def _sic(html):
    return [re.sub(r"<[^>]+>", "", s).strip() for s in
            re.findall(r'id="sic\d"[^>]*>(.*?)</span>', html, re.S)]


def _officers(num):
    try:
        ho = fetch(f"{BASE}/{num}/officers", accept="text/html")
    except Exception:
        return []
    # split into appointment blocks by officer link
    blocks = re.split(r'<a[^>]+href="/officers/', ho)[1:]
    out = []
    for b in blocks:
        nm = re.match(r'[^"]+"[^>]*>(.*?)</a>', b)
        name = _html.unescape(re.sub(r"<[^>]+>|\s+", " ", nm.group(1)).strip()) if nm else ""
        if not name:
            continue
        resigned = "Resigned on" in b[:1500]
        role = (re.search(r'Role\s*</dt>\s*<dd[^>]*>\s*([^<]+)', b, re.I) or [None, ""])[1].strip()
        occ = (re.search(r'Occupation\s*</dt>\s*<dd[^>]*>\s*([^<]+)', b, re.I) or [None, ""])[1].strip()
        appt = (re.search(r'Appointed on\s*</dt>\s*<dd[^>]*>\s*([^<]+)', b, re.I) or [None, ""])[1].strip()
        out.append({"name": name, "role": role, "occupation": occ,
                    "appointed": appt, "active": not resigned})
    return out


def run():
    cands = [r for r in store.all_candidates() if r["discovery_source_class"] == "uk-companies-house"]
    print(f"Traversing {len(cands)} UK candidates...")
    done = 0
    for r in cands:
        raw = json.loads(r["raw"])
        num = raw.get("ch_number")
        if not num:
            continue
        try:
            html = fetch(f"{BASE}/{num}", accept="text/html")
        except Exception as e:
            store.audit(r["dedup_key"], r["firm_legal_name"], "uk-traverse", "", f"profile fetch failed: {e}")
            continue
        sics = _sic(html)
        officers = _officers(num)
        active = [o for o in officers if o["active"]]
        codes = [s.split(" - ")[0].strip() for s in sics]
        fo_relevant = any(c in FO_RELEVANT_SIC for c in codes)
        non_fo = any(c.startswith(NON_FO_SIC_PREFIX) for c in codes)
        sic_flag = ("fo-relevant-sic" if fo_relevant else
                    "non-fo-sic" if non_fo else "ambiguous-sic")

        raw.update({"sic": sics, "officers": officers, "sic_flag": sic_flag})
        rec = Record(
            record_id=r["record_id"],
            firm_legal_name=r["firm_legal_name"],
            investing_sectors="; ".join(sics),
            caveats=(f"UK filing SIC: {sic_flag}. Active officers: "
                     + ", ".join(f"{o['name']} ({o['role'] or o['occupation']})" for o in active[:5])
                     if active else f"UK filing SIC: {sic_flag}. No active officers listed."),
        )
        store.upsert(rec, raw=raw)
        done += 1
        if done % 15 == 0:
            print(f"  traversed {done}...")
    print(f"Done. Traversed {done} UK profiles.")


if __name__ == "__main__":
    run()
