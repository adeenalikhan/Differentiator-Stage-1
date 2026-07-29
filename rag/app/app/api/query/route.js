import { retrieve, SUFFICIENCY, META } from "../../../lib/retrieval.js";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60; // Vercel Hobby max; free models can queue for 10-30s

// LLM grounding is the intended path. Give the (slow, free) model real time to finish so we
// return an LLM-grounded answer; the extractive path is only a last-resort safety net if the
// model errors or exceeds the budget entirely. See README/METHODOLOGY: free-model latency caveat.
const LLM_BUDGET_MS = 48000; // total time allowed for LLM grounding before falling back
const PER_CALL_MS = 40000;   // per-model attempt cap

// Currently-free OpenRouter models, tried in order (resilient to a slug being deprecated —
// which is exactly how the first deploy failed). Override with OPENROUTER_MODEL.
const MODELS = [
  process.env.OPENROUTER_MODEL,
  "openai/gpt-oss-20b:free",
  "google/gemma-4-31b-it:free",
  "nvidia/nemotron-nano-9b-v2:free",
  "mistralai/mistral-7b-instruct:free",
].filter(Boolean);

// Compact, grounded view of a record for the model / extractive answer.
function recordContext(r) {
  const contact = r.principal_email
    ? `${r.principal_email} (${r.email_status})`
    : r.principal_linkedin ? r.principal_linkedin
    : r.principal_phone ? `${r.principal_phone} (firm line)`
    : "no direct contact on file (private office)";
  return [
    `FIRM: ${r.firm_common_name} [${r.fo_type}]${r.family_affiliation ? " — " + r.family_affiliation : ""}`,
    `LOCATION: ${[r.hq_city, r.hq_region, r.hq_country].filter(Boolean).join(", ")}`,
    r.aum ? `AUM: ${r.aum}` : "",
    r.investing_sectors ? `SECTORS/THESIS: ${r.investing_sectors}` : "",
    `PRINCIPAL: ${r.principal_full_name || "—"}${r.principal_title ? ", " + r.principal_title : ""}`,
    `CONTACT: ${contact}`,
    r.signals ? `RECENT (dated): ${r.signals}` : "",
  ].filter(Boolean).join("\n");
}

// Edge-weighted ordering: most-relevant chunks at the START and END, weaker in the middle
// ("lost in the middle"). candidates are already sorted best-first.
function edgeOrder(cands) {
  const front = [], back = [];
  cands.forEach((c, i) => (i % 2 === 0 ? front.push(c) : back.unshift(c)));
  return front.concat(back);
}

function extractiveAnswer(query, cands) {
  const lines = cands.slice(0, 5).map((c, i) => {
    const r = c.record;
    const contact = r.principal_email || r.principal_linkedin || r.principal_phone || "no direct contact (private office)";
    return `${i + 1}. ${r.firm_common_name} — ${r.fo_type}${r.family_affiliation ? ` (${r.family_affiliation})` : ""}, `
      + `${r.hq_country}. Principal: ${r.principal_full_name || "—"}${r.principal_title ? ", " + r.principal_title : ""}. `
      + `Contact: ${contact}.${r.signals ? " Recent: " + r.signals.split(".")[0] + "." : ""}`;
  });
  return `Here ${cands.length === 1 ? "is" : "are"} the closest ${Math.min(5, cands.length)} matching `
    + `family ${cands.length === 1 ? "office" : "offices"} in the dataset:\n\n` + lines.join("\n\n");
}

async function llmAnswer(query, ordered) {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key) return { text: null, debug: "no OPENROUTER_API_KEY set" };
  const context = ordered.map((c, i) => `--- Record ${i + 1} ---\n${recordContext(c.record)}`).join("\n\n");
  const system = "You are a family-office intelligence assistant for a fund's investor-relations team. "
    + "Answer ONLY from the RECORDS provided. Cite the firm names you use. If a record lacks a contact, say so plainly "
    + "(do not invent an email, phone, or name). If the records do not contain enough to answer, say you don't have "
    + "enough verified information rather than guessing. Never state a fact, number, or contact that is not in the records. "
    + "Keep it concise and practical: who to contact, why them, and why now. "
    + "Write in short prose and simple bullet lines (start bullets with '- '); do NOT use markdown tables.";
  const messages = [
    { role: "system", content: system },
    { role: "user", content: `QUESTION: ${query}\n\nRECORDS:\n${context}` },
  ];
  const headers = {
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    "HTTP-Referer": "https://differentiator-stage-1-six.vercel.app",
    "X-Title": "Family Office Intelligence",
  };
  const start = Date.now();
  let lastErr = "no models tried";
  for (const model of MODELS) {
    const left = LLM_BUDGET_MS - (Date.now() - start);
    if (left < 1500) { lastErr = "llm budget exhausted -> extractive fallback"; break; }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), Math.min(PER_CALL_MS, left));
    try {
      const resp = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST", headers, signal: controller.signal,
        body: JSON.stringify({ model, temperature: 0.2, max_tokens: 500, messages }),
      });
      if (!resp.ok) { lastErr = `HTTP ${resp.status} (${model}): ${(await resp.text()).slice(0, 140)}`; continue; }
      const j = await resp.json();
      const text = j.choices?.[0]?.message?.content?.trim();
      if (text) return { text, debug: `ok (${model}, ${Date.now() - start}ms)` };
      lastErr = `empty completion (${model})`;
    } catch (e) {
      lastErr = String(e).includes("abort") ? `timeout (${model})` : `fetch error (${model}): ${String(e).slice(0, 100)}`;
    } finally { clearTimeout(timer); }
  }
  return { text: null, debug: lastErr };
}

export async function POST(req) {
  const t0 = Date.now();
  let query = "";
  try { ({ query } = await req.json()); } catch {}
  query = (query || "").toString().slice(0, 400).trim();
  if (!query) return Response.json({ status: "empty", message: "Please enter a question." }, { status: 400 });

  const { candidates, top, filters } = retrieve(query, 8);

  // Sufficiency gate — the working control: decline rather than answer weakly.
  if (top < SUFFICIENCY || candidates.length === 0) {
    log({ query, top, gate: "decline", filters, ms: Date.now() - t0 });
    return Response.json({
      status: "decline",
      message: "This tool answers only from its 50 verified family-office records, so it can't help "
        + "with general questions. Ask about family offices instead — try a type (single- or "
        + "multi-family), a country, a sector (e.g. venture, real estate), a recent-activity query, "
        + "or a specific family or firm name.",
      meta: META,
    });
  }

  const ordered = edgeOrder(candidates.slice(0, 6));
  const llm = await llmAnswer(query, ordered);
  const answer = llm.text || extractiveAnswer(query, candidates);
  const mode = llm.text ? "llm-grounded" : "extractive-grounded";

  const sources = candidates.slice(0, 5).map((c) => ({
    firm: c.record.firm_common_name, type: c.record.fo_type,
    family: c.record.family_affiliation, country: c.record.hq_country,
    principal: c.record.principal_full_name, title: c.record.principal_title,
    email: c.record.principal_email, email_status: c.record.email_status,
    linkedin: c.record.principal_linkedin, phone: c.record.principal_phone,
    aum: c.record.aum, signals: c.record.signals, tier: c.record.completeness_tier,
    basis: c.record.is_fo_evidence, proof: c.record.fo_proof_strength,
    score: Math.round(c.score * 10) / 10,
  }));

  log({ query, top, gate: "answer", mode, llm: llm.debug, candidates: sources.map((s) => `${s.firm}:${s.score}`), ms: Date.now() - t0 });
  return Response.json({ status: candidates.length ? "answer" : "partial", answer, mode, sources, filters, meta: META });
}

// Audit log — every retrieval call (query, scores, gate, mode, latency). Vercel captures stdout.
function log(o) { try { console.log("[RAG]", JSON.stringify(o)); } catch {} }
