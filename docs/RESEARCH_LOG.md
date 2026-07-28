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

### [2026-07-28] discovery — SEC 13F harvester (built + run)
- Goal: turn the 13F vein into a real candidate pool in the store.
- Method: `pipeline/discovery/sec_13f.py`. Two bugs found and fixed during the run:
    1. **EDGAR company-name search is prefix-only** — `company=family office` matches only
       names *starting* with it ("Family Office Research LLC"), not "Duquesne Family
       Office". So name-search is near-useless here; full-text is the workhorse. Kept but
       demoted.
    2. **FTS page size is 100, not 10** — my first loop stepped `from` by 10 and re-read the
       same first 100 filings, yielding only 42 distinct. Real usable range is `from=0..890`
       (from=990 returns 0). Fixed to step by 100.
- Result: **53 distinct SEC-13F candidates** stored. 31 self-signal as family offices by
  name (incl. Duquesne/Druckenmiller, Louis-Dreyfus, Callan, Biltmore, Custos). ~5 clear
  false positives present (Bank of Montreal, Deutsche Bank, AQR, Bryn Mawr Bank) — their
  13F info tables contain the phrase but they are not family offices; these will be rejected
  in Phase 2 classification.
- Decision: SEC-13F is a sufficient anchor (need only <=~17 of the final 50 from any one
  class). Do NOT try to squeeze more from 13F phrase search — it structurally misses
  hidden-name SFOs. Move to independent sources next: SEC Form D (different filer
  population: private-placement issuers, and it lists related persons = free principals),
  then non-SEC/non-US (UK Companies House public site, Singapore, press/conference).

### [2026-07-28] discovery — UK Companies House (public site, no key)
- Goal: an independent, non-US population to break SEC's blind spot.
- Method: `pipeline/discovery/uk_companies_house.py` scrapes the public advanced-search
  results (no login/key needed), paginated, keeping only status=Active. User could not
  register for a CH API key (no GOV.UK One Login account); public site fully sufficient.
- Result: **53 active UK candidates.** Quality is mixed: genuine-looking SFOs (Wedgwood,
  Davidoff Frey, Blu) next to service/insurance firms (Simon Family Office Insures,
  Weybridge Family Office Services) and micro-entities.
- Honest caveats logged now, not hidden: (1) UK name-search shares the hidden-name blind
  spot — substantive UK SFOs are often NOT named "family office", so this source
  under-covers the real UK market; (2) parser bug leaks a "SIC codes -" line into the city
  field for some rows — cosmetic, will be corrected in enrichment from each firm's clean
  profile page. Expect heavy Rule-2 rejection here.
- Decision: 53 UK candidates is enough raw material; do not over-mine a noisy source. Next:
  a genuinely different mechanism for hidden-name SFOs (press/known-family + conference
  rosters) and a Singapore slice for the "global" claim.

### [2026-07-28] entity-enrichment — SEC 13F filing traversal
- Goal: extract verified facts from each 13F filer's authoritative document.
- Method: `pipeline/enrichment/sec_13f_traverse.py` fetches primary_doc.xml + information
  table per candidate.
- Result: **52/53 traversed.** Each now carries verified legal name, HQ address, a named
  signatory + title + phone, portfolio value (as an explicit AUM FLOOR — 13(f) equities
  only), position count, report quarter, and top holdings (dated signals). Surfaced a
  non-US SFO (Marcuard, Zurich) filing 13F.
- Honest finding: **most signatories are CCO/CFO/COO/GC, not the investment principal.**
  E.g. Duquesne's 13F is signed by GC Sue Meng, but the decision-maker is Druckenmiller. So
  the signatory is stored as a verified associated person + firm phone; the true investment
  principal is resolved separately in principal enrichment. Not upgrading a compliance
  signatory to "principal" is a deliberate honesty choice.

### [2026-07-28] classification — UK Companies House profile + officers traversal
- Goal: classify UK candidates against their actual filings, not their names.
- Method: `pipeline/enrichment/uk_traverse.py` fetches each firm's profile (SIC codes) +
  officers page (active directors).
- Result of SIC-based pre-classification on 53 UK firms: **17 FO-relevant SIC** (fund mgmt
  66300, financial holding 64205/64209, investment trusts 64301/64304 — Blu, Wedgwood,
  Crew, Schwarz, Freedman...), **24 non-FO SIC** (property 68xxx, insurance 65xxx, legal
  69xxx → likely rejects), **12 ambiguous**. Active officers captured as principal
  candidates (e.g. Blu's founder Christian Armbrüster appears as a director). Did NOT
  auto-assign a principal — UK FOs use corporate/nominee directors, so the real
  decision-maker is chosen in enrichment.
- Decision: realistic UK qualifying pool ~15-20, confirming the "expect heavy rejection"
  prediction. UK name-search is noisy but the SIC filter makes the cut defensible and
  evidence-based.

### [2026-07-28] principal/contact — calibration research agent (running)
- Goal: before scaling enrichment across ~100 firms, calibrate what is actually findable
  under a free-only budget on 6 firms (Duquesne, Louis-Dreyfus, Boston, Callan, Arrowroot,
  Custos), spanning SFO and MFO.
- Method: a research agent instructed to return only strictly-sourced facts (URL per value),
  identify the TRUE investment principal (not the 13F signatory), and NEVER pattern-generate
  an email — published individual emails only, else honest "unresolved" with attempts. Writes
  to `data/raw/enrichment/batch_cal.json`, ingested through `ingest_research.py`, which
  enforces mechanical no-fabrication gates (drops generic mailboxes, non-/in/ LinkedIn URLs,
  downgrades "verified" emails lacking a source).
- Result: pending (agent running). Will review output critically before fanning out.
- Manual calibration (me, not the pipeline) already confirmed: Duquesne = SFO, no website,
  Druckenmiller principal, email likely unresolved; Louis-Dreyfus = SFO, disambiguated from
  the Louis Dreyfus commodities company. These manual checks inform the agent instructions;
  the shipped values will be pipeline-produced, not hand-typed.

### [2026-07-28] principal/contact — calibration results + independent verification
- Agent returned 6 sourced records. Quality was high and, importantly, HONEST:
    - Correctly reclassified Boston / Callan / Arrowroot / Custos as **MFOs**, not SFOs,
      despite the "family office" branding (789 client accounts at Boston; $50M-min UHNW
      client base at Callan). Only Duquesne + Louis-Dreyfus are true SFOs.
    - **Refused to ship guessed emails**: excluded a ZoomInfo masked pattern (Boston) and a
      RocketReach broker listing (Arrowroot) as not published/attested — exactly the rule.
    - Flagged Louis-Dreyfus family branch as INFERRED (entity-confusion with the LDC
      commodities firm) and its 13F as lapsed since Q3 2022 (stale signal).
    - Flagged that Custos's true investment decision-maker is CIO Lopiccolo, not signatory
      Herr.
- **Independent verification (me, re-fetching the cited pages):**
    - callanfamilyoffice.com/team/jack-ginter/ → confirms `jginter@callanfo.com`. ✓
    - custosfo.com team bios → confirm `mitchell@custosfo.com` + `anthony@custosfo.com`. ✓
  The agent did not fabricate. Approach validated end-to-end (discover → traverse → enrich →
  gate → verify), no duplicate rows created.
- Email hit-rate: **2/6 firms** (both MFOs with team pages); 0/2 SFOs — confirms the SFO/MFO
  completeness asymmetry predicted in METHODOLOGY §1.5. Consequence for strategy: to earn the
  "SFO prize" the file must lean on press/hidden-name discovery for SFO *count*, and accept
  honest email blanks on those high-value records.
- Two pipeline bugs found + fixed: research JSON used `legal_name` (aliased), and the
  ingester's upsert could spawn a duplicate row once enrichment added a domain (added
  `update_by_record_id`, which never recomputes the dedup key).

### [2026-07-28] principal/contact — FAILED attempt: recursive agent delegation
- Goal: scale enrichment by running research agents over 12-firm (13F) and 9-firm (UK)
  batches in parallel.
- What happened: the batch agents, given a longer firm list, decided to "parallelize" by
  spawning their OWN sub-agents (children named "Research 3 family offices A/B/D") instead of
  doing the research themselves. Those children in turn tried to delegate again. The whole
  tree returned "I'll wait for the other agents to finish" and **wrote no output files**.
  ~250k tokens spent for zero records.
- Why: the 6-firm calibration agent did the work itself and succeeded; the larger batches
  tripped a coordinator instinct. Lesson: a general-purpose agent with the Agent/Task tool
  will over-delegate when the task looks big.
- Fix: relaunched with (1) an explicit "do ALL research yourself; do NOT use the Agent/Task
  tool; do not spawn or wait on sub-agents" instruction at the top, and (2) batches capped at
  6. Recorded here rather than hidden — it's a real cost and a real lesson about orchestrating
  research agents.

### [2026-07-28] usage limit + pivot to deterministic enrichment
- Mid-run we hit the account usage limit (resets ~07:40 Asia/Karachi); the model-based
  research agents failed with API errors. Key realization: direct HTTP calls (urllib to SEC
  EDGAR, Companies House, SEC IAPD) are NOT model calls and do not consume that budget.
- Pivot: enrich the pending SEC-13F set deterministically via the SEC IAPD adviser API.
  Signal: a firm that files a 13F but has NO adviser registration essentially must rely on the
  single-family-office exemption (rule 202(a)(11)(G)-1) -> strong SFO signal; a registered
  adviser serves clients -> MFO-vs-FO left to the research pass (avoids mislabeling a wealth
  manager / research firm as a family office).
- Result across 47 pending 13F candidates: **35 registered advisers** (verified CRD/SEC#/
  address added; left pending), **2 unregistered -> qualified SFO** (Intrepid, Kopp; family
  not yet named — flagged), **10 ambiguous** (left pending). IAPD firm-detail endpoint is
  gated (HTTP 403), so the search API (registration + address) is the usable signal.
- Honest read: pure unregistered SFOs filing 13F are RARE — most "X Family Office" 13F filers
  are registered MFOs. This is why SFO count grows slowly and why press/hidden-name SFO
  discovery matters; that agent was stopped by the limit before writing output and must be
  re-run after reset.
- State at pause: 106 discovered+traversed; 14 qualified (8 SFO / 5 MFO / 1 Undetermined),
  2 verified individual emails; 3 rejected; 89 pending enrichment.
