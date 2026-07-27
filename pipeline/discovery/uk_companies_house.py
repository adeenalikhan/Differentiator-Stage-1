"""UK Companies House discoverer (public advanced-search site, no API key).

Independent, non-US population. Noisy: a UK company named "... Family Office ..." may be
a genuine SFO, an MFO, or a service provider. Discovery keeps them all; Rule-2
classification filters later. Registered-office address and officer names (fetched in
enrichment) are the useful proof material.
"""
from __future__ import annotations
import re, sys, html as _html
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch
from pipeline.common.schema import Record
from pipeline.common import store

BASE = "https://find-and-update.company-information.service.gov.uk/advanced-search/get-results"


def _parse_rows(html):
    rows = re.split(r'<tr class="govuk-table__row">', html)[1:]
    out = []
    for r in rows:
        m = re.search(r'href=/company/(\S+?)[ >].*?>([^<]+?)<span', r, re.S)
        if not m:
            m = re.search(r'href=/company/(\S+?)[ >][^>]*>([^<]+?)</a>', r, re.S)
        if not m:
            continue
        num, name = m.group(1).strip(), _html.unescape(m.group(2).strip())
        status = (re.search(r'font-weight-bold">([^<]+)<', r) or [None, ""])[1].strip()
        inc = re.search(r'(\d{4,8}[A-Z]?)\s*-\s*Incorporated on ([^<]+)<', r)
        inc_date = inc.group(2).strip() if inc else ""
        ctype = (re.search(r'<li>([^<]*(?:company|partnership|LLP|LP)[^<]*)</li>', r, re.I) or [None, ""])[1].strip()
        # address: last non-empty <li> often holds the registered office
        lis = [ _html.unescape(x.strip()) for x in re.findall(r'<li>([^<]*)</li>', r) ]
        addr = next((x for x in reversed(lis) if "," in x and "Incorporated" not in x), "")
        out.append({"number": num, "name": name, "status": status,
                    "type": ctype, "incorporated": inc_date, "address": addr})
    return out


def run(pages=6, only_active=True):
    store.init_db()
    added = 0
    for page in range(1, pages + 1):
        url = f"{BASE}?companyNameIncludes=family+office&page={page}"
        try:
            html = fetch(url, accept="text/html")
        except Exception as e:
            print(f"  page {page} ERR {e}"); break
        rows = _parse_rows(html)
        if not rows:
            print(f"  page {page}: no rows, stopping."); break
        page_added = 0
        for r in rows:
            if only_active and r["status"].lower() != "active":
                continue
            # crude UK address -> city/postcode split (registered office)
            parts = [p.strip() for p in r["address"].split(",") if p.strip()]
            city = parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")
            rec = Record(
                record_id=f"UKCH-{r['number']}",
                firm_legal_name=r["name"],
                firm_common_name=r["name"].title() if r["name"].isupper() else r["name"],
                discovery_source_class="uk-companies-house",
                discovery_source_detail=f"Companies House {r['number']} ({r['type']}); inc. {r['incorporated']}",
                discovery_url=f"https://find-and-update.company-information.service.gov.uk/company/{r['number']}",
                hq_city=city,
                hq_country="United Kingdom",
            )
            store.upsert(rec, raw={"ch_number": r["number"], "ch_status": r["status"],
                                   "ch_type": r["type"], "ch_incorporated": r["incorporated"],
                                   "ch_address": r["address"]})
            added += 1; page_added += 1
        print(f"  page {page}: {len(rows)} rows, {page_added} active kept")
    print(f"Done. Upserted {added} UK Companies House candidates.")
    return added


if __name__ == "__main__":
    run()
