// Stage-1 retrieval: structured filters + lexical BM25-ish scoring over the 50 records.
// This is a faithful port of rag/prototype.py, which was validated against real queries.
import data from "../data/records.json";

const RECORDS = data.records;

const STOP = new Set(("the a an of in to for and or with on at is are be by from as into over your you "
  + "who what which where how do does can me i we they them their his her show find list give").split(" "));
const COUNTRIES = ["united states", "usa", "us", "uk", "united kingdom", "britain", "singapore",
  "france", "germany", "switzerland", "denmark", "india", "australia", "canada", "hong kong",
  "indonesia", "europe", "asia"];
const SECTORS = ["venture", "vc", "private equity", "real estate", "crypto", "hedge", "technology",
  "tech", "healthcare", "biotech", "energy", "public equit", "credit", "infrastructure"];
const COUNTRY_CANON = { usa: "united states", us: "united states", britain: "united kingdom", uk: "united kingdom" };

function tokenize(s) {
  return (s.toLowerCase().match(/[a-z0-9]+/g) || []).filter((t) => !STOP.has(t) && t.length > 1);
}

// precompute document frequency for idf
const DF = new Map();
for (const r of RECORDS) {
  for (const t of new Set(tokenize(r.search_text))) DF.set(t, (DF.get(t) || 0) + 1);
}
const N = RECORDS.length;
const idf = (t) => Math.log(1 + (N - (DF.get(t) || 0) + 0.5) / ((DF.get(t) || 0) + 0.5));

export function parseFilters(q) {
  const ql = q.toLowerCase();
  const f = { countries: [], sectors: [] };
  if (/\bsingle[- ]family\b|\bsfo\b/.test(ql)) f.fo_type = "SFO";
  else if (/\bmulti[- ]family\b|\bmfo\b/.test(ql)) f.fo_type = "MFO";
  f.countries = COUNTRIES.filter((c) => new RegExp("\\b" + c.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b").test(ql));
  f.sectors = SECTORS.filter((s) => ql.includes(s));
  f.recent = /\brecent|latest|2026|2025|new|activity|signal/.test(ql);
  f.contact = /\bcontact|email|reach|phone|linkedin\b/.test(ql);
  return f;
}

export function retrieve(query, k = 8) {
  const qt = tokenize(query);
  const f = parseFilters(query);
  const ql = query.toLowerCase();
  const ranked = RECORDS.map((r) => {
    const tf = new Map();
    for (const t of tokenize(r.search_text)) tf.set(t, (tf.get(t) || 0) + 1);
    let s = 0;
    for (const t of qt) { const c = tf.get(t) || 0; if (c) s += idf(t) * (c / (c + 1.5)); }
    // strong boost for family / firm / principal name mentions (entity queries e.g. "Bill Gates")
    const entityBlob = (r.family_affiliation + " " + r.firm_common_name + " " + r.principal_full_name).toLowerCase();
    for (const t of qt) if (t.length > 2 && entityBlob.includes(t)) s += 3;
    // structured filters / boosts
    if (f.fo_type) s = r.fo_type === f.fo_type ? s + 3 : s * 0.15;
    for (const c of f.countries) { const cc = COUNTRY_CANON[c] || c; if ((r.hq_country || "").toLowerCase().includes(cc)) s += 4; }
    for (const sec of f.sectors) {
      if ((r.investing_sectors + " " + r.investment_thesis + " " + r.description).toLowerCase().includes(sec)) s += 2;
    }
    if (f.recent && r.signals) s += 1;
    if (f.contact && (r.principal_email || r.principal_linkedin || r.principal_phone)) s += 1;
    return { score: s, record: r };
  }).sort((a, b) => b.score - a.score);
  return { candidates: ranked.slice(0, k), top: ranked[0]?.score || 0, filters: f };
}

export const SUFFICIENCY = 2.0; // min top score to attempt an answer; else decline
export const ALL_RECORDS = RECORDS;
export const META = data.meta;
