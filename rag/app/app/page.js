"use client";
import { useState } from "react";

const EXAMPLES = [
  "Single-family offices in Singapore",
  "Family offices investing in venture capital and technology",
  "Who runs Jeff Bezos's family office and how do I reach them?",
  "US multi-family offices with a contactable principal",
  "Family offices with recent 2026 activity",
];

// Lightweight inline markdown: **bold**, *italic*, and URLs -> clickable links.
function inline(text) {
  const re = /\*\*(.+?)\*\*|\*(.+?)\*|(https?:\/\/[^\s)]+)/g;
  const out = []; let last = 0, m, k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(<span key={k++}>{text.slice(last, m.index)}</span>);
    if (m[1]) out.push(<strong key={k++}>{m[1]}</strong>);
    else if (m[2]) out.push(<em key={k++}>{m[2]}</em>);
    else out.push(<a key={k++} href={m[3]} target="_blank" rel="noreferrer">{m[3].replace(/^https?:\/\//, "").replace(/\/$/, "")}</a>);
    last = re.lastIndex;
  }
  if (last < text.length) out.push(<span key={k++}>{text.slice(last)}</span>);
  return out;
}

// Render the answer with structure: "- " lines become firm bullets; "why now" lines become
// muted sub-text; everything else is a paragraph. (LLM output is markdown-ish.)
function renderRich(text) {
  return (text || "").split("\n").map((l) => l.trim()).filter(Boolean).map((l, i) => {
    if (/^[-*]\s+/.test(l)) return <p key={i} className="ans-item">{inline(l.replace(/^[-*]\s+/, ""))}</p>;
    if (/^\*?\s*why\s*now/i.test(l)) return <p key={i} className="ans-sub">{inline(l)}</p>;
    return <p key={i}>{inline(l)}</p>;
  });
}

function StatusBadge({ status }) {
  const map = {
    verified: ["Verified", "#166534", "#dcfce7"],
    "returned-by-provider": ["Provider-returned", "#9a3412", "#ffedd5"],
    "catch-all": ["Catch-all", "#854d0e", "#fef9c3"],
    unverified: ["Unverified", "#854d0e", "#fef9c3"],
    unresolved: ["No email on file", "#475569", "#f1f5f9"],
  };
  const [label, fg, bg] = map[status] || ["", "#475569", "#f1f5f9"];
  if (!label) return null;
  return <span style={{ fontSize: 11, fontWeight: 600, color: fg, background: bg, padding: "2px 8px", borderRadius: 999 }}>{label}</span>;
}

function SourceCard({ s }) {
  const contact = s.email
    ? <span>✉ <a href={`mailto:${s.email}`}>{s.email}</a> <StatusBadge status={s.email_status} /></span>
    : s.linkedin ? <span>in <a href={s.linkedin} target="_blank" rel="noreferrer">LinkedIn profile</a></span>
    : s.phone ? <span>☎ {s.phone} <span className="muted">(firm line)</span></span>
    : <span className="muted">No direct contact — private office (documented gap)</span>;
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="firm">{s.firm}</div>
          {s.family ? <div className="muted small">{s.family}</div> : null}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span className={"pill " + (s.type === "SFO" ? "pill-sfo" : s.type === "MFO" ? "pill-mfo" : "pill-und")}>{s.type}</span>
          {s.tier ? <span className="pill pill-tier" title="Completeness tier">{s.tier}</span> : null}
        </div>
      </div>
      <div className="grid">
        <div><span className="lbl">Decision-maker</span>{s.principal || "—"}{s.title ? <span className="muted">, {s.title}</span> : ""}</div>
        <div><span className="lbl">Contact</span>{contact}</div>
        {s.aum ? <div><span className="lbl">AUM</span>{s.aum}</div> : null}
        <div><span className="lbl">Location</span>{s.country}</div>
      </div>
      {s.signals ? <div className="signals"><span className="lbl">Why now</span>{s.signals}</div> : null}
      {s.basis ? <details className="why"><summary>Why this is a family office</summary><p>{s.basis} <span className="muted">(proof: {s.proof})</span></p></details> : null}
    </div>
  );
}

export default function Home() {
  const [q, setQ] = useState("");
  const [state, setState] = useState({ status: "idle" });
  const [loading, setLoading] = useState(false);

  async function run(query) {
    const question = (query ?? q).trim();
    if (!question) return;
    setQ(question); setLoading(true); setState({ status: "idle" });
    try {
      const r = await fetch("/api/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: question }) });
      setState(await r.json());
    } catch {
      setState({ status: "error", message: "Something went wrong reaching the service. Please try again." });
    } finally { setLoading(false); }
  }

  return (
    <main>
      <header>
        <h1>Family Office Intelligence</h1>
        <p className="sub">Search {state.meta?.count || 50} verified single- and multi-family office records — decision-makers, contacts, and recent activity. Every answer is grounded in the underlying records.</p>
      </header>

      <div className="searchbar">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run()} placeholder="e.g. single-family offices in Singapore investing in tech" aria-label="Search" />
        <button onClick={() => run()} disabled={loading}>{loading ? "Searching…" : "Search"}</button>
      </div>
      <div className="chips">{EXAMPLES.map((e) => <button key={e} className="chip" onClick={() => run(e)}>{e}</button>)}</div>

      {loading && <div className="note">Searching the dataset and generating a grounded answer… this can take 10–30s on the free model.</div>}

      {state.status === "decline" && <div className="panel warn"><strong>No confident answer from the dataset.</strong><p>{state.message}</p></div>}
      {state.status === "empty" && <div className="panel warn">{state.message}</div>}
      {state.status === "error" && <div className="panel err">{state.message}</div>}

      {(state.status === "answer" || state.status === "partial") && (
        <>
          <div className="panel answer">
            <div className="answer-head"><span>Answer</span><span className="mode" title="How the answer was produced">{state.mode === "llm-grounded" ? "grounded (LLM)" : "grounded (extractive)"}</span></div>
            <div className="answer-body">{renderRich(state.answer)}</div>
          </div>
          <div className="sources-label">Sources ({state.sources.length}) — the records this answer is built from</div>
          <div className="sources">{state.sources.map((s) => <SourceCard key={s.firm} s={s} />)}</div>
        </>
      )}

      <footer>Grounded in a {state.meta?.count || 50}-record dataset ({state.meta ? Object.entries(state.meta.source_mix || {}).map(([k, v]) => `${v} ${k}`).join(" · ") : "multi-source"}). Answers never assert facts the records don't support.</footer>
    </main>
  );
}
