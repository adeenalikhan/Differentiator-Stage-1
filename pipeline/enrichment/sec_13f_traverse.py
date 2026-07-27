"""Traverse each SEC-13F candidate's authoritative filing and extract verified facts.

From primary_doc.xml: legal name, HQ address, signatory (name/title/phone), portfolio
total value + position count + report quarter. From the information table: top holdings.

Epistemic care baked in:
  * The 13F "value" is US-listed 13(f) securities only -> a FLOOR on AUM, never total AUM.
    Stored in `signals` (dated), not asserted as `aum` unless clearly labelled as a floor.
  * The signatory is a verified *associated person*; whether they are THE investment
    decision-maker is decided in principal enrichment, not assumed here. Title is recorded
    verbatim so an MFO ops signatory isn't dressed up as the principal.
"""
from __future__ import annotations
import sys, json, re, html as _html
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch, fetch_json
from pipeline.common.schema import Record
from pipeline.common import store

US_STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
                "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())


def _tag(xml, tag):
    m = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.S | re.I)
    return _html.unescape(m.group(1).strip()) if m else ""


def _cover(cik, acc):
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/primary_doc.xml"
    xml = fetch(url, accept="application/xml")
    sig = _tag(xml, "signatureBlock")
    return {
        "name": _tag(xml, "name"),
        "street1": _tag(xml, "street1"),
        "city": _tag(xml, "city"),
        "state": _tag(xml, "stateOrCountry"),
        "zip": _tag(xml, "zipCode"),
        "sig_name": _tag(sig, "name"),
        "sig_title": _tag(sig, "title"),
        "sig_phone": _tag(sig, "phone"),
        "value_thousands": _tag(xml, "tableValueTotal"),
        "positions": _tag(xml, "tableEntryTotal"),
        "quarter": _tag(xml, "reportCalendarOrQuarter"),
    }, url


def _top_holdings(cik, acc, n=5):
    """Find the information table xml via index.json and sum top holdings by value."""
    try:
        idx = fetch_json(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json")
    except Exception:
        return []
    itfile = None
    for it in idx.get("directory", {}).get("item", []):
        nm = it.get("name", "")
        if nm.endswith(".xml") and "primary_doc" not in nm:
            itfile = nm; break
    if not itfile:
        return []
    try:
        xml = fetch(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{itfile}", accept="application/xml")
    except Exception:
        return []
    agg = {}
    for m in re.finditer(r"<infoTable>(.*?)</infoTable>", xml, re.S | re.I):
        blk = m.group(1)
        issuer = _tag(blk, "nameOfIssuer")
        val = _tag(blk, "value").replace(",", "")
        try:
            agg[issuer] = agg.get(issuer, 0) + int(val)
        except ValueError:
            pass
    top = sorted(agg.items(), key=lambda x: -x[1])[:n]
    return top  # [(issuer, value_thousands)]


def run(only_name_fo=False):
    cands = [r for r in store.all_candidates() if r["discovery_source_class"] == "sec-13f"]
    print(f"Traversing {len(cands)} SEC-13F candidates...")
    done = 0
    for r in cands:
        raw = json.loads(r["raw"])
        cik = int(raw["cik"]); f = raw.get("latest_13f")
        if not f:
            continue
        if only_name_fo and not raw.get("name_signals_fo"):
            continue
        acc = f["accession"].replace("-", "")
        try:
            cov, url = _cover(cik, acc)
        except Exception as e:
            store.audit(r["dedup_key"], r["firm_legal_name"], "13f-traverse", "", f"cover fetch failed: {e}")
            continue
        holdings = _top_holdings(cik, acc)
        # dated portfolio signal
        val_b = ""
        if cov["value_thousands"].isdigit():
            val_b = f"${int(cov['value_thousands'])/1e6:.2f}B"
        sig_txt = ""
        if val_b:
            sig_txt = (f"13F portfolio {val_b} across {cov['positions']} US-listed positions "
                       f"as of {cov['quarter']} (floor on AUM, 13(f) securities only)")
        if holdings:
            tops = "; ".join(f"{h[0]} (${h[1]/1e6:.2f}B)" for h in holdings[:5])
            sig_txt += f". Top holdings: {tops}"

        state = cov["state"]
        country = "United States of America" if state in US_STATES else state
        region = state if state in US_STATES else ""

        upd = Record(
            record_id=r["record_id"],
            firm_legal_name=cov["name"] or r["firm_legal_name"],
            firm_common_name=r["firm_common_name"],
            hq_street=cov["street1"],
            hq_city=cov["city"] or r["hq_city"],
            hq_region=region or r["hq_region"],
            hq_country=country or r["hq_country"],
            # signatory -> provisional principal (title recorded verbatim; verified later)
            principal_full_name=cov["sig_name"],
            principal_title=cov["sig_title"],
            principal_relevance=(f"Signed the firm's Form 13F-HR ({cov['quarter']}) as "
                                 f"{cov['sig_title']} — verified associated person; investment-"
                                 f"decision-maker status to be confirmed separately."),
            principal_phone=cov["sig_phone"],
            phone_source=f"SEC Form 13F-HR signature block, {url}",
            signals=sig_txt,
            signals_dates=cov["quarter"],
            signals_source=f"SEC EDGAR 13F-HR {f['accession']} ({f['date']})",
        )
        raw["cover"] = cov
        raw["top_holdings"] = holdings
        store.upsert(upd, raw=raw)
        done += 1
        if done % 15 == 0:
            print(f"  traversed {done}...")
    print(f"Done. Traversed {done} SEC-13F filings.")


if __name__ == "__main__":
    run()
