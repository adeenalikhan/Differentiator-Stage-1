"""SEC 13F-HR discoverer (US anchor).

Two complementary discovery methods, merged and deduped by CIK:
  A. EDGAR company-name search for family-office name patterns (high precision).
  B. EDGAR full-text search for the phrase "family office" in 13F-HR (broad net).

Then each distinct CIK is hydrated from data.sec.gov/submissions for business address,
SIC, former names, and its latest 13F filing (kept for signal extraction later).

Discovery only proves the firm EXISTS and filed a 13F. Whether it is truly a family
office (and SFO vs MFO) is decided later in classification (Rule 2).
"""
from __future__ import annotations
import re, sys, json
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch, fetch_json
from pipeline.common.schema import Record
from pipeline.common import store

NAME_PATTERNS = [
    "family office", "family capital", "family partners", "family investment",
    "family holdings", "family enterprises", "family group", "family wealth",
]
FTS = "https://efts.sec.gov/LATEST/search-index"


def _company_name_search(pattern):
    """browse-edgar atom company search -> [(cik, name)]. Matches name substring."""
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
           f"&company={pattern.replace(' ', '+')}&type=13F&dateb=&owner=include"
           "&count=100&output=atom")
    try:
        xml = fetch(url, accept="application/atom+xml")
    except Exception as e:
        print(f"  [name:{pattern}] ERR {e}"); return []
    out = []
    # atom entries carry <cik> and <company-info>/<conformed-name> or <title>
    for m in re.finditer(r"<cik>(\d+)</cik>.*?<(?:conformed-name|name)>([^<]+)</", xml, re.S):
        out.append((m.group(1).zfill(10), m.group(2).strip()))
    # fallback: simpler single-entity page format
    if not out:
        for m in re.finditer(r"CIK=(\d+).*?companyName\">([^<]+)", xml):
            out.append((m.group(1).zfill(10), m.group(2).strip()))
    return out


def _fts_entities(phrases=("family office", "single family office", "our family's",
                           "the family office of", "manages the family")):
    """Page FTS by 100 (its real page size). Widen with several phrases to reach 13F
    filers that describe themselves as a family office without those exact words in
    a name."""
    seen = {}
    for phrase in phrases:
        q = "%22" + phrase.replace(" ", "+").replace("'", "%27") + "%22"
        for frm in range(0, 1000, 100):
            url = f'{FTS}?q={q}&forms=13F-HR&from={frm}'
            try:
                data = fetch_json(url)
            except Exception as e:
                print(f"  [fts '{phrase}' from={frm}] ERR {e}"); break
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                break
            for h in hits:
                for nm in h.get("_source", {}).get("display_names", []):
                    m = re.match(r"^(.*?)\s+\(CIK\s+(\d+)\)", nm)
                    if m:
                        seen[m.group(2).zfill(10)] = m.group(1).strip()
        print(f"  phrase '{phrase}': pool now {len(seen)} distinct CIKs")
    return seen


def _hydrate(cik):
    """Pull entity details from the submissions API."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        d = fetch_json(url)
    except Exception as e:
        return None
    biz = (d.get("addresses") or {}).get("business") or {}
    recent = (d.get("filings") or {}).get("recent") or {}
    forms = recent.get("form", [])
    latest_13f = None
    for i, f in enumerate(forms):
        if f and f.startswith("13F"):
            latest_13f = {
                "accession": recent["accessionNumber"][i],
                "date": recent["filingDate"][i],
                "primaryDoc": recent.get("primaryDocument", [""] * len(forms))[i],
            }
            break
    state_or_country = biz.get("stateOrCountry", "")
    return {
        "name": d.get("name", ""),
        "sic": d.get("sicDescription", ""),
        "former_names": [fn.get("name") for fn in d.get("formerNames", [])],
        "city": biz.get("city", ""),
        "state_or_country": state_or_country,
        "latest_13f": latest_13f,
        "website": d.get("website", ""),
    }


# US state codes vs foreign -> country resolution for stateOrCountry field
US_STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
                "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())


def run(limit=None):
    store.init_db()
    entities = {}  # cik -> (name, method)
    print("Method A: company-name search")
    for pat in NAME_PATTERNS:
        for cik, name in _company_name_search(pat):
            entities.setdefault(cik, (name, "name-search"))
        print(f"  after '{pat}': {len(entities)} distinct entities")
    print("Method B: full-text 13F search")
    for cik, name in _fts_entities().items():
        entities.setdefault(cik, (name, "fts"))
    print(f"Total distinct CIKs: {len(entities)}")

    if limit:
        entities = dict(list(entities.items())[:limit])

    added = 0
    for cik, (name, method) in entities.items():
        info = _hydrate(cik)
        if not info:
            continue
        nm = info["name"] or name
        soc = info["state_or_country"]
        country = "United States of America" if soc in US_STATES else (soc or "")
        region = soc if soc in US_STATES else ""
        rec = Record(
            record_id=f"SEC13F-{cik}",
            firm_legal_name=nm,
            firm_common_name=nm.title() if nm.isupper() else nm,
            discovery_source_class="sec-13f",
            discovery_source_detail=f"EDGAR 13F filer (CIK {cik}); discovered via {method}",
            discovery_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F",
            hq_city=info["city"],
            hq_region=region,
            hq_country=country,
        )
        raw = {"cik": cik, "sic": info["sic"], "former_names": info["former_names"],
               "latest_13f": info["latest_13f"], "discovery_method": method,
               "name_signals_fo": bool(re.search(r"family\s+(office|capital|partners|wealth)", nm, re.I))}
        store.upsert(rec, raw=raw)
        added += 1
        if added % 25 == 0:
            print(f"  hydrated {added}...")
    print(f"Done. Upserted {added} SEC 13F candidates.")
    return added


if __name__ == "__main__":
    run()
