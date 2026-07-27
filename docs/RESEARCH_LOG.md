# Research Execution Log

Append-only. Newest entries at the bottom. This is a log of what was *attempted*, not a
retrospective of what worked. Failed attempts are recorded on purpose — a claim that
something "could not be found" is only credible with the failed attempts behind it.

**Entry format**

```
### [YYYY-MM-DD HH:MM] <phase> — <source/tool>
- Goal:
- Method / query:
- Result: (counts, or what came back / what failed)
- Decision: (what I did next, and why)
```

Phases: `discovery` · `entity-enrichment` · `principal` · `contact` · `signal` ·
`validation` · `rag`.

---

### [2026-07-28] setup — repository & plan
- Goal: commit the pre-build plan before any data work, so the methodology's "before I
  built anything" section is real and not reconstructed.
- Method: git init; wrote `docs/METHODOLOGY.md` Part 1, this log, and the record schema.
- Result: foundation committed. Discovery not yet started.
- Decision: anchor discovery on SEC Form ADV (family-office-exemption filers) as the first
  proof-capable source, then deliberately branch to independent non-US sources to avoid the
  single-source trap. First probe: SEC EDGAR full-text search.
