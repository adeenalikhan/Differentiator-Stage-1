# Family Office Dataset + Micro-RAG

An AI pipeline that **discovers** real family offices from independent public sources,
**enriches** them with entity / principal / signal intelligence, **validates** the
high-value cells so that failed checks actually change what ships, and **serves** the
result through a grounded natural-language search product.

The dataset is the product. The pipeline is how it is built and kept honest. The RAG is
the delivery mechanism.

## Repository map

| Path | What it is |
|------|------------|
| `docs/METHODOLOGY.md` | Begins with the plan **as it stood before building**, then where it held and broke. |
| `docs/RESEARCH_LOG.md` | Append-only log of every source/tool/query attempted — failures included. |
| `docs/VALIDATION_CHAINS.md` | Three records traced end to end: discovery → extraction → enrichment → validation → confidence. |
| `docs/AI_SESSIONS.md` | AI-session scope statement + the key prompt templates given to the models. |
| `docs/TASK2_SAAS_CONVERSION_ANALYSIS.md` | Task 2: the SaaS free-to-paid conversion analysis + reasoning. |
| `rag/app/` | Live Micro-RAG (Next.js on Vercel): retrieval + grounded answers + decline gate + UI. |
| `pipeline/` | The system: discovery, enrichment, validation, export. |
| `data/raw/` | Candidate pool, tagged by the source class that found each firm. |
| `data/audit/` | Rejected firms and rejected cell values (never shipped, kept for honesty). |
| `data/final/` | The 50-record deliverable (CSV + XLSX). |
| `rag/` | Retrieval, grounding control, API. |
| `web/` | Customer-facing search UI (deployed). |

## Status

Under active construction. See `docs/METHODOLOGY.md` for current state.
