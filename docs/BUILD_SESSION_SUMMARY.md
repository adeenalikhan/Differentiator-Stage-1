# Build Session Summary

## 1. Approximate build time

Roughly 9 to 10 hours of active work across four sessions,
spanning 07-28 03:00 to 07-29 19:00 within the 48-hour window. The long gaps between sessions
were usage-limit pauses and overnight, not work.

## 2. Main work sessions

1. 07-28 morning (\~1h): repo and pre-build plan, SEC 13F and UK Companies House discovery,
first record traversal, a 6-firm calibration, and the validation/export machinery.
2. 07-28 afternoon/evening (\~4h): deterministic enrichment (SEC IAPD, UK PSC), the
registered-13F batches, and hidden-name SFO discovery, reaching 50 qualified firms.
3. 07-29 early (\~3h): the balanced final 50 (Singapore slice, 13F phones, a LinkedIn pass that
swapped figureheads for reachable executives), the full Micro-RAG build, Vercel deploy, and
fixes found by testing the live system.
4. 07-29 later (\~0.5h): line-by-line audits of each deliverable against the brief, plus Task 2.

## 3. Major components: what the AI produced vs. what I changed or decided

* Direction and constraints were mine: dataset-first, free-tier only, global mix, Vercel. The
AI built the pipeline (discoverers, traversers, enrichers, the release-gating validator, the
exporter) and the RAG app; I set what it optimized for.
* Sourcing: the AI proposed an SEC ADV anchor. Testing broke that, and I held the multi-source
rule that capped any one source at 34% and forced the press and Singapore discovery angles.
* Contacts: I flagged that every verified email sat on an MFO. That drove the decision to add
13F firm phones and replace billionaire figureheads with the reachable CIO/CEO (I chose to do
both rather than rebalance the file), while refusing any fabricated or pattern-guessed email.
* RAG: the AI wrote the retrieval and answer code. I caught that Gemini now requires billing
(moved to OpenRouter), required answers to stay LLM-grounded rather than fall back to
extractive (accepting the documented free-model latency), and confirmed that declining
off-topic questions is correct scope behavior, not a bug.
* Audits: I asked for each deliverable to be checked against the brief line by line, which
surfaced real corrections, including a "7 verified emails" over-count (actually 6 plus 1
unverified) and a RAG design doc that overclaimed versus the shipped app.

