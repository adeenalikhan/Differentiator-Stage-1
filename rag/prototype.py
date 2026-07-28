"""Prototype + validate the retrieval algorithm against the real 50 records BEFORE mirroring
it in the deployable JS app (Node absent locally, so this is how we de-risk).

Stage 1: structured filters (type / country / sector / AUM / recency) + lexical BM25-ish
scoring over each record's search_text. Returns ranked candidates + a top score used by the
sufficiency gate. Stage 2 (LLM rerank + grounded answer) is done in the app via OpenRouter;
here we just validate that stage 1 surfaces the right records for representative queries.
"""
import json, os, re, math
from collections import Counter

REC = json.load(open(os.path.join(os.path.dirname(__file__), "app", "data", "records.json"),
                     encoding="utf-8"))["records"]

STOP = set("the a an of in to for and or with on at is are be by from as into over your you "
           "who what which where how do does can me i we they them their his her".split())
COUNTRIES = ["united states", "usa", "us", "uk", "united kingdom", "britain", "singapore",
             "france", "germany", "switzerland", "denmark", "india", "australia", "canada",
             "hong kong", "indonesia", "europe", "asia"]
SECTORS = ["venture", "vc", "private equity", "real estate", "crypto", "hedge", "technology",
           "tech", "healthcare", "biotech", "energy", "public equit", "credit", "infrastructure"]


def tokenize(s):
    return [t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t) > 1]


# precompute idf over the corpus
_DF = Counter()
for r in REC:
    for t in set(tokenize(r["search_text"])):
        _DF[t] += 1
_N = len(REC)


def _idf(t):
    return math.log(1 + (_N - _DF.get(t, 0) + 0.5) / (_DF.get(t, 0) + 0.5))


def parse_filters(q):
    ql = q.lower()
    f = {}
    if re.search(r"\bsingle[- ]family\b|\bsfo\b", ql):
        f["fo_type"] = "SFO"
    elif re.search(r"\bmulti[- ]family\b|\bmfo\b", ql):
        f["fo_type"] = "MFO"
    f["countries"] = [c for c in COUNTRIES if re.search(r"\b" + re.escape(c) + r"\b", ql)]
    f["sectors"] = [s for s in SECTORS if s in ql]
    f["recent"] = bool(re.search(r"\brecent|latest|2026|2025|new|just\b|activity|signal", ql))
    f["contact"] = bool(re.search(r"\bcontact|email|reach|phone|linkedin\b", ql))
    return f


_COUNTRY_CANON = {"usa": "united states", "us": "united states", "britain": "united kingdom",
                  "uk": "united kingdom"}


def score(q):
    qt = tokenize(q)
    f = parse_filters(q)
    ranked = []
    for r in REC:
        txt = r["search_text"]
        tf = Counter(tokenize(txt))
        s = sum(_idf(t) * (tf.get(t, 0) / (tf.get(t, 0) + 1.5)) for t in qt)
        # structured boosts / filters
        if f.get("fo_type"):
            s = s + 3 if r["fo_type"] == f["fo_type"] else s * 0.15  # near-hard filter
        for c in f["countries"]:
            cc = _COUNTRY_CANON.get(c, c)
            if cc in (r["hq_country"] or "").lower():
                s += 4
        for sec in f["sectors"]:
            if sec in (r["investing_sectors"] + " " + r["investment_thesis"] + " " + r["description"]).lower():
                s += 2
        if f["recent"] and r["signals"]:
            s += 1
        if f["contact"] and (r["principal_email"] or r["principal_linkedin"] or r["principal_phone"]):
            s += 1
        ranked.append((s, r))
    ranked.sort(key=lambda x: -x[0])
    return ranked, f


SUFFICIENCY = 2.0  # min top score to attempt an answer (else decline)

if __name__ == "__main__":
    tests = [
        "single family offices in Singapore",
        "family offices investing in venture capital and technology",
        "who runs Bill Gates's family office and how do I reach them",
        "multi family offices in the US with a contactable principal",
        "family offices with recent 2026 investment activity",
        "UK single family offices",
        "family offices in Brazil",  # expect nothing -> decline
    ]
    for q in tests:
        ranked, f = score(q)
        top = ranked[:4]
        gate = "ANSWER" if top[0][0] >= SUFFICIENCY else "DECLINE (low confidence)"
        print(f"\nQ: {q}\n  filters={ {k:v for k,v in f.items() if v} }  gate={gate}  topscore={top[0][0]:.1f}")
        for s, r in top:
            print(f"    {s:5.1f}  {r['firm_common_name'][:34]:34} {r['fo_type']:4} {r['hq_country'][:18]}")
