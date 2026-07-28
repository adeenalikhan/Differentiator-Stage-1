# Family Office Intelligence — Micro-RAG

Customer-facing search over the 50-record family-office dataset. Built for a non-technical
investor-relations user: ask a question in plain English, get a grounded answer plus the
source records it was built from. Answers never assert facts the records don't support.

## Stack
- **Next.js 14** (App Router) on **Vercel** — one page + one API route; clean separation of
  presentation (`app/page.js`), retrieval/data (`lib/retrieval.js`, `data/records.json`), and
  answer generation (`app/api/query/route.js`).
- **No paid dependency.** Retrieval runs in-process; final phrasing uses a **free OpenRouter
  model** if a key is present, and falls back to a **keyless extractive answer** if not.

## Chunking & retrieval
- **Chunking:** record-level. Each family office is one structured "card" (firm, type,
  principal, contact, AUM, sectors, dated signals). With 50 records, record-level chunks keep
  each answer traceable to a whole, verifiable entity rather than a fragment.
- **Stage 1 — structured + lexical:** parse the query for type (SFO/MFO), country, sector,
  recency and contact intent; score every record with BM25-ish lexical similarity + field
  boosts + an entity-name boost (so "Bill Gates's office" pins Cascade). Validated against
  real queries in `rag/prototype.py`.
- **Stage 2 — rerank + grounded answer:** the top candidates are reranked and phrased by the
  LLM under a strict grounding prompt (answer only from provided records, cite firms, decline
  if insufficient). A distilled cross-encoder reranker is specced in `docs/RAG_DESIGN.md` as a
  latency/cost optimization; the LLM performs cross-encoder-style joint scoring today.
- **Context ordering:** most-relevant records placed at the **start and end** of the context
  ("lost in the middle"), not the center.

## Grounding control (the working control, not just a prompt)
- **Sufficiency gate:** if the best lexical score is below threshold, the system **declines**
  with a helpful message instead of answering weakly (test: "family offices in Brazil").
- **Extractive fallback** (no key): the answer is composed *from record fields only*, so it
  **cannot hallucinate** — the strongest possible grounding guarantee.
- Every email carries its verification status; private-office contact gaps are shown as
  honest "no direct contact on file," never invented.

## Deploy (Vercel)
1. Import the GitHub repo into Vercel.
2. Set **Root Directory** = `rag/app`.
3. Add env var **`OPENROUTER_API_KEY`** (from openrouter.ai). Optional: `OPENROUTER_MODEL`
   (defaults to a free model). Without a key the app still runs in extractive-grounded mode.
4. Deploy. (Next.js auto-detected; no other config.)

## Testing
- Retrieval: `npm run eval` (recall@k on labelled queries) — mirrors `rag/prototype.py`.
- Answer layer (faithfulness): run the live queries below against the deployed URL and check
  each answer only states what the source cards contain, and that thin-evidence queries decline.

## What works / doesn't / would improve
- **Works:** structured+lexical retrieval surfaces the right records (validated); the decline
  path fires on out-of-scope queries; extractive mode guarantees no fabrication.
- **Doesn't (yet):** semantic recall is lexical-only in stage 1 (no vector index) — fine for
  50 records, would miss paraphrase at larger scale.
- **Would improve:** add the distilled cross-encoder reranker + a vector index for scale;
  add per-answer citation highlighting; log to a store rather than stdout.

## Live queries run against the deployed system
_(filled in after deploy — the actual queries used to reach the conclusions above)_
