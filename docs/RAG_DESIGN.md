# Micro-RAG design spec (Phase 5)

Production-shaped requirements for the customer-facing RAG. Incorporates directed
hardening steps, with engineering notes where a step needed correction — recorded so the
reasoning is auditable, not silently applied.

> Scope note: these are properties of the RAG/query system. They are NOT fixes for the
> discovery/enrichment research agents (those failed on usage limits and recursive
> delegation, handled separately via anti-delegation prompts, ≤3 concurrent streams, and
> resume-to-write salvage). A reranker/eval harness does not make a web-research agent
> "never fail." Kept distinct on purpose.

## 1. Two-stage retrieval with a cross-encoder reranker
- Stage 1 (recall): embed the query, retrieve a WIDE candidate set (top ~50 field/record
  chunks) by vector similarity + structured filters (fo_type, geography, AUM band).
- Stage 2 (precision): cross-encoder rerank the wide set, keep the top ~5–8 for the answer.
- **Correction applied:** the request said "rerank top 20 → top 50"; that widens, which
  defeats a reranker. A reranker narrows: retrieve-wide → rerank → keep-few. With only 50
  records, recall is easy; the reranker's job is field-level precision (right principal /
  right signal), so it matters most at the chunk level.
- Free options: a local `cross-encoder/ms-marco-MiniLM` (sentence-transformers) at query
  time, or a free-tier rerank API. No paid dependency.

## 2. Bounded loops + tested fallback
- Hard cap on retrieval/generation rounds (≤2). If the sufficiency gate (below) is not met
  after the cap, return a fixed, human-readable fallback — never an error dump or raw JSON.
- **Test the failure path before deploy:** an explicit test that a no-evidence query yields
  the graceful fallback, not a crash or a hallucinated answer.

## 3. Automated evals on every deploy (both layers)
- A small labelled eval set (queries → expected record IDs / expected "cannot answer").
- Metrics: **retrieval recall@k** (did the right record make the candidate set?) and
  **answer faithfulness/groundedness** (does the generated answer assert ONLY what the
  retrieved, trusted records support?).
- Runs pre-deploy in CI; a regression blocks the deploy. Tests the dataset layer AND the
  answer layer, per the assessment's "test the answers your system gives users."

## 4. Grounding/sufficiency gate ("autonomous ≠ unsupervised")
- The query path is READ-ONLY, so there is no irreversible action to gate there. The
  operative control is a **sufficiency gate**: the system qualifies, limits, or DECLINES an
  answer when retrieved evidence is insufficient — a working control, not just a prompt
  instruction. This is the assessment's required "control that limits what an answer may
  claim."
- For any write/outreach path (out of scope here), a human approval gate is required before
  the irreversible action. Recorded so the principle is on file.

## 5. Context ordering — relevance to the EDGES, not the center
- **Correction applied:** the request said "most important content in the center." The
  "lost in the middle" result (Liu et al., 2023) is the opposite — LLMs attend best to the
  START and END of the context and worst to the MIDDLE. So the top reranked chunks are
  placed at the beginning and end of the prompt context; lower-relevance filler goes in the
  middle. Putting the crucial record in the center would be the weakest position.

## 6. Full retrieval logging / audit
- Every query logs: timestamp, raw query, candidate chunk IDs + similarity scores, reranked
  order + scores, the final assembled context, the model response, and the gate decision
  (answered / qualified / declined). Enables audit, eval replay, and debugging.

## Stack (free-tier, deployable — Phase 5)
- Embeddings precomputed at build (50 records → tiny); vectors stored in-repo/JSON or
  pgvector. Query embedding + generation via a free-tier key (Gemini/Groq). Cross-encoder
  local. Next.js UI on Vercel with clear success / partial / empty / declined states.
