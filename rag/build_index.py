"""Build the RAG index the app consumes: export the selected final-50 records to a clean
JSON with a searchable text blob per record. Run from repo root: python rag/build_index.py

No embeddings are stored here — retrieval is structured + lexical (stage 1) then LLM
relevance rerank + grounded answer (stage 2). With 50 records this is fast and, crucially,
deployable without any local ML runtime (Node/torch absent on the build machine).
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pipeline.export.export_dataset import select

OUT = os.path.join(os.path.dirname(__file__), "app", "data", "records.json")

FIELDS = [
    "record_id", "firm_common_name", "fo_type", "family_affiliation", "website",
    "corporate_linkedin", "description", "investment_thesis", "investing_sectors",
    "aum", "hq_city", "hq_region", "hq_country",
    "principal_full_name", "principal_title", "principal_linkedin",
    "principal_email", "email_status", "principal_phone",
    "signals", "signals_dates", "completeness_tier", "caveats",
    # provenance (used for grounding + a "why trust this" view, not for keyword search)
    "discovery_source_class", "is_fo_evidence", "fo_proof_strength",
]

SEARCH_FIELDS = ["firm_common_name", "fo_type", "family_affiliation", "description",
                 "investment_thesis", "investing_sectors", "aum", "hq_city", "hq_region",
                 "hq_country", "principal_full_name", "principal_title", "signals"]


def build():
    chosen, per_class, n_qual = select()
    out = []
    for r in chosen:
        rec = {k: (r.get(k) or "") for k in FIELDS}
        rec["search_text"] = " ".join(str(r.get(f) or "") for f in SEARCH_FIELDS).lower()
        out.append(rec)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"records": out, "meta": {
            "count": len(out), "source_mix": per_class, "qualified_pool": n_qual,
            "built": "2026-07-29"}}, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(out)} records -> {OUT}")
    print("source mix:", per_class)


if __name__ == "__main__":
    build()
