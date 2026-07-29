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
- **Embedding model: none — by design.** At 50 records, lexical + structured retrieval matches
  the right records reliably (validated in `rag/prototype.py`) without the cost, cold-start, and
  bundling risk of a vector model in a keyless serverless deploy. A build-time embedding model +
  vector index is the documented upgrade for larger corpora (`docs/RAG_DESIGN.md`, tagged SPEC).
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
- **Free-model latency (stated caveat):** the answer layer uses a **free** OpenRouter model
  (`openai/gpt-oss-20b:free`), which frequently **queues for 10–30s**. This is a cost decision
  (no paid key), not a design flaw. We choose to **wait for the LLM-grounded answer** (function
  budget 48s / `maxDuration` 60s) rather than downgrade quality; a keyless **extractive-grounded**
  answer is served only as a last-resort safety net if the model errors or exceeds the budget.
  With a paid/faster model key, responses would be 1–3s — swap it in via `OPENROUTER_MODEL`.
- **Would improve:** faster/paid model for latency; distilled cross-encoder reranker + a vector
  index for scale; per-answer citation highlighting; log to a store rather than stdout.

## Live queries run against the deployed system
Run against https://differentiator-stage-1-six.vercel.app on 2026-07-29 (mode: `llm-grounded`,
model `openai/gpt-oss-20b:free`). These are the actual queries used to validate the answer layer:

1. **"single-family offices in Singapore investing in technology"** → answered with Weybourne
   (Dyson) and other Singapore SFOs, each with its tech thesis, dated activity, and contact.
   Retrieval correctly filtered to SFO + Singapore.
2. **"who runs Jeff Bezos's family office and how do I reach them"** → *"Bezos Expeditions —
   Principal: Melinda Lewison, Managing Director — LinkedIn: …"*, citing Record 1. Correctly
   returns the reachable professional, not the figurehead; no invented email.
3. **"US multi-family offices with a verified email contact"** → *"Pioneer Family Office —
   verified email avin@piowealth.com"*. Surfaces a record whose email is actually verified.
4. **"family offices in Brazil"** → **declined**: "I don't have a record in this dataset that
   confidently answers that…". The sufficiency gate fired instead of fabricating — the key
   answer-layer test.

**Conclusions from these runs:** retrieval surfaces the right records for type/geo/sector and
entity-name queries; the answer layer stays within the records (no invented contacts, cites
records); and thin-evidence queries decline rather than hallucinate. Bugs found and fixed via
this live testing: a deprecated free model slug (added a resilient fallback list), an
entity-name boost that defeated the decline gate on generic words, and a markdown-table answer
format that the plain-text UI rendered as raw pipes.
