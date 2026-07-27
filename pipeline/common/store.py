"""SQLite candidate/audit store. One row per candidate firm.

The store is the pipeline's working memory: discovery writes candidates, enrichment
updates them, validation may reject them (moving evidence to the audit log). The final
50 are exported from here — never hand-assembled.
"""
from __future__ import annotations
import json, os, sqlite3, re
from dataclasses import fields
from typing import Optional
from .schema import Record

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pipeline.db")
DB_PATH = os.path.abspath(DB_PATH)

_RECORD_COLS = [f.name for f in fields(Record)]


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = connect()
    cols = ",\n  ".join(f'"{c}" TEXT' for c in _RECORD_COLS)
    con.executescript(f"""
    CREATE TABLE IF NOT EXISTS candidates (
      dedup_key TEXT PRIMARY KEY,
      status    TEXT DEFAULT 'candidate',   -- candidate | qualified | rejected
      raw       TEXT DEFAULT '{{}}',        -- extra source payload (holdings, etc.)
      {cols}
    );
    CREATE TABLE IF NOT EXISTS audit (
      ts        TEXT,
      dedup_key TEXT,
      firm      TEXT,
      field     TEXT,        -- which cell/decision
      value     TEXT,        -- the rejected value
      reason    TEXT         -- why it was rejected / not shipped
    );
    """)
    con.commit(); con.close()


def norm_key(name: str = "", domain: str = "") -> str:
    """Dedup key: prefer domain, else normalized name."""
    if domain:
        d = domain.lower().strip()
        d = re.sub(r"^www\.", "", d)
        return "d:" + d
    n = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
    n = re.sub(r"(llc|lp|inc|ltd|llp|pte|gmbh|ag|company|co|the)$", "", n)
    return "n:" + n


def upsert(rec: Record, raw: Optional[dict] = None, status: Optional[str] = None):
    key = norm_key(rec.firm_common_name or rec.firm_legal_name, rec.domain)
    con = connect()
    existing = con.execute("SELECT dedup_key FROM candidates WHERE dedup_key=?", (key,)).fetchone()
    data = rec.to_dict()
    if existing:
        # update only non-empty incoming fields (enrichment shouldn't clobber with blanks)
        sets, vals = [], []
        for c in _RECORD_COLS:
            if data.get(c):
                sets.append(f'"{c}"=?'); vals.append(data[c])
        if raw is not None:
            sets.append('"raw"=?'); vals.append(json.dumps(raw))
        if status:
            sets.append('"status"=?'); vals.append(status)
        if sets:
            vals.append(key)
            con.execute(f"UPDATE candidates SET {', '.join(sets)} WHERE dedup_key=?", vals)
    else:
        cols = ["dedup_key", "status", "raw"] + _RECORD_COLS
        vals = [key, status or "candidate", json.dumps(raw or {})] + [data.get(c, "") for c in _RECORD_COLS]
        con.execute(f'INSERT INTO candidates ({",".join(chr(34)+c+chr(34) for c in cols)}) '
                    f'VALUES ({",".join("?" for _ in cols)})', vals)
    con.commit(); con.close()
    return key


def audit(dedup_key: str, firm: str, field: str, value: str, reason: str, ts: str = "2026-07-28"):
    con = connect()
    con.execute("INSERT INTO audit (ts,dedup_key,firm,field,value,reason) VALUES (?,?,?,?,?,?)",
                (ts, dedup_key, firm, field, value, reason))
    con.commit(); con.close()


def all_candidates(status: Optional[str] = None):
    con = connect()
    q = "SELECT * FROM candidates"
    if status:
        q += " WHERE status=?"
        rows = con.execute(q, (status,)).fetchall()
    else:
        rows = con.execute(q).fetchall()
    con.close()
    return [dict(r) for r in rows]


def counts():
    con = connect()
    rows = con.execute("SELECT status, COUNT(*) n FROM candidates GROUP BY status").fetchall()
    by_source = con.execute(
        "SELECT discovery_source_class, COUNT(*) n FROM candidates GROUP BY discovery_source_class"
    ).fetchall()
    con.close()
    return {r["status"]: r["n"] for r in rows}, {r["discovery_source_class"]: r["n"] for r in by_source}


if __name__ == "__main__":
    init_db()
    print("DB initialized at", DB_PATH)
