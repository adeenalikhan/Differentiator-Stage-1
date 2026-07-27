"""Discovery PROBE (not the final discoverer): test whether SEC EDGAR full-text search
surfaces family offices, and via which form types.

Hypothesis to test:
  * ADV-exemption SFOs file nothing -> weak for the purest SFOs.
  * Form 13F-HR (managers >$100M in 13(f) securities) drags many SFOs into a free,
    searchable index, with holdings attached as recent-activity signals.

This script only prints; it does not write to the dataset.
"""
import json, sys, time
import urllib.request

UA = "FamilyOfficeResearch adeen@digitalanchormedia.com"  # SEC requires a descriptive UA
FTS = "https://efts.sec.gov/LATEST/search-index?q=%22family+office%22"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def distinct_entities(form="13F-HR", phrase="family office", max_pages=12):
    """Paginate FTS, collect DISTINCT filing entities (by CIK)."""
    import re
    q = '%22' + phrase.replace(" ", "+") + '%22'
    seen = {}
    name_hits = {}  # entities whose *name* contains the phrase (high precision)
    for page in range(max_pages):
        url = f"https://efts.sec.gov/LATEST/search-index?q={q}&forms={form}&from={page*10}"
        try:
            data = get(url)
        except Exception as e:
            print("  page err:", e); break
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            break
        for h in hits:
            for nm in h.get("_source", {}).get("display_names", []):
                m = re.match(r"^(.*?)\s+\(CIK\s+(\d+)\)", nm)
                if not m:
                    continue
                name, cik = m.group(1).strip(), m.group(2)
                seen[cik] = name
                if re.search(r"family\s+office|family\s+capital|family\s+partners", name, re.I):
                    name_hits[cik] = name
        time.sleep(0.3)
    return seen, name_hits


if __name__ == "__main__":
    total = get(f"https://efts.sec.gov/LATEST/search-index?q=%22family+office%22&forms=13F-HR"
                ).get("hits", {}).get("total", {}).get("value")
    print(f"13F-HR filings mentioning 'family office': {total}")
    seen, name_hits = distinct_entities()
    print(f"distinct filing entities sampled (first ~120 filings): {len(seen)}")
    print(f"  of which NAME itself signals a family office: {len(name_hits)}")
    print("\nHigh-precision (name-based) sample:")
    for cik, name in list(name_hits.items())[:25]:
        print(f"    {cik}  {name}")
