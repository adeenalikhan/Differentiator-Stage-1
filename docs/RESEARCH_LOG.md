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

### [2026-07-28] discovery — SEC EDGAR full-text search (probe)
- Goal: test whether SEC surfaces family offices, and via which form type.
- Method: `efts.sec.gov/LATEST/search-index` exact phrase "family office", faceted by form;
  then paginated to collect DISTINCT filing entities by CIK (`sec_edgar_probe.py`).
- Result:
    - ALL forms: 10,000+ matches. **13F-HR: 893 filings. Form D: 261. ADV: 0.**
    - First ~120 13F filings = 35 distinct entities; **29 self-identify as a family office
      in their name.** Sample included Duquesne Family Office (Druckenmiller SFO) and
      Louis-Dreyfus Family Office (both genuine SFOs), alongside MFOs (Pathstone, Geller,
      Callan, Arrowroot).
- Decision: **13F-HR is a confirmed, high-value discovery vein** — it forces >$100M SFOs
  into a free index and its holdings double as dated signals. Adopt it as the US anchor.
  Two cautions carried forward: (1) name-based matches mix SFO+MFO, so every entity still
  needs Rule-2 classification; (2) SFOs filing under non-obvious names (e.g. Cascade =
  Gates, Bezos Expeditions) won't appear via the "family office" phrase and need a separate
  reverse-discovery angle.

### [2026-07-28] discovery — SEC Form ADV assumption (BROKEN)
- Goal: use ADV / family-office-exemption filers as the proof anchor (per initial plan §1.4).
- Result: **ADV returns 0 in EDGAR full-text search** — ADV lives in the separate IARD/IAPD
  system, not EDGAR. More importantly, SFOs relying on the family-office exemption
  (rule 202(a)(11)(G)-1) are excluded from the Advisers Act and **file no ADV at all**, so
  the purest SFOs are structurally invisible there.
- Decision: demote ADV from "anchor." It remains useful for registered MFOs/RIAs via
  adviserinfo.sec.gov (separate fetch, not EDGAR FTS), but it cannot be the SFO backbone.
  This is the first place the plan broke on contact; logged to METHODOLOGY Part 2.
