// Automated retrieval eval — recall@k on labelled queries. Run: npm run eval (needs Node).
// Self-contained (reads records.json via fs) so it runs in CI without the Next runtime.
// Mirrors the stage-1 logic in lib/retrieval.js; the Python rag/prototype.py is the
// primary validated reference. Answer-faithfulness (needs the LLM) is checked separately
// against the deployed endpoint — see README "Testing the answer layer".
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const dir = dirname(fileURLToPath(import.meta.url));
const RECORDS = JSON.parse(readFileSync(join(dir, "..", "data", "records.json"), "utf-8")).records;

const STOP = new Set("the a an of in to for and or with on at is are be by from as into over your you who what which where how do does can me i we they them their his her show find list give".split(" "));
const tok = (s) => (s.toLowerCase().match(/[a-z0-9]+/g) || []).filter((t) => !STOP.has(t) && t.length > 1);
const ESTOP = new Set("family office offices capital partners group holdings management ventures venture investment investments invest advisors advisers fund funds llc ltd inc lp company co holding global services trust wealth private".split(" "));
const DF = new Map();
for (const r of RECORDS) for (const t of new Set(tok(r.search_text))) DF.set(t, (DF.get(t) || 0) + 1);
const N = RECORDS.length, idf = (t) => Math.log(1 + (N - (DF.get(t) || 0) + 0.5) / ((DF.get(t) || 0) + 0.5));

function retrieve(q, k = 5) {
  const qt = tok(q), ql = q.toLowerCase();
  const sfo = /\bsingle[- ]family\b|\bsfo\b/.test(ql), mfo = /\bmulti[- ]family\b|\bmfo\b/.test(ql);
  const ranked = RECORDS.map((r) => {
    const tf = new Map(); for (const t of tok(r.search_text)) tf.set(t, (tf.get(t) || 0) + 1);
    let s = 0; for (const t of qt) { const c = tf.get(t) || 0; if (c) s += idf(t) * (c / (c + 1.5)); }
    const eb = (r.family_affiliation + " " + r.firm_common_name + " " + r.principal_full_name).toLowerCase();
    for (const t of qt) if (t.length > 2 && !ESTOP.has(t) && eb.includes(t)) s += 3;
    if (sfo) s = r.fo_type === "SFO" ? s + 3 : s * 0.15;
    if (mfo) s = r.fo_type === "MFO" ? s + 3 : s * 0.15;
    for (const c of ["singapore", "united kingdom", "united states", "france", "germany", "denmark", "india", "australia", "canada", "hong kong", "switzerland"])
      if (ql.includes(c.split(" ")[0]) && (r.hq_country || "").toLowerCase().includes(c)) s += 4;
    return { s, r };
  }).sort((a, b) => b.s - a.s);
  return ranked.slice(0, k);
}

// Labelled cases: query -> a substring that MUST appear in a top-k firm/family, or "DECLINE".
const CASES = [
  ["single-family offices in Singapore", "singapore-country"],
  ["UK single family offices", "uk-country"],
  ["family office of Bill Gates", "cascade"],
  ["Soros family office", "soros"],
  ["multi-family offices in the US", "mfo-us"],
  ["family offices investing in venture capital", "venture"],
  ["family offices in Brazil", "DECLINE"],
];
const SUFFICIENCY = 2.0;

let pass = 0;
for (const [q, expect] of CASES) {
  const top = retrieve(q, 5);
  let ok;
  if (expect === "DECLINE") ok = (top[0]?.s || 0) < SUFFICIENCY;
  else if (expect === "singapore-country") ok = top.some((x) => (x.r.hq_country || "").toLowerCase().includes("singapore"));
  else if (expect === "uk-country") ok = top.some((x) => (x.r.hq_country || "").toLowerCase().includes("united kingdom"));
  else if (expect === "mfo-us") ok = top.some((x) => x.r.fo_type === "MFO" && (x.r.hq_country || "").includes("United States"));
  else if (expect === "venture") ok = top.some((x) => (x.r.investing_sectors + x.r.investment_thesis + x.r.description).toLowerCase().includes("vent"));
  else ok = top.some((x) => (x.r.firm_common_name + x.r.family_affiliation).toLowerCase().includes(expect));
  console.log(`${ok ? "PASS" : "FAIL"}  "${q}"  -> top: ${top.slice(0, 3).map((x) => x.r.firm_common_name).join(" | ")}`);
  if (ok) pass++;
}
console.log(`\nRetrieval recall@5: ${pass}/${CASES.length}`);
process.exit(pass === CASES.length ? 0 : 1);
