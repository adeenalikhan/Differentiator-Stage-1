# Methodology

> This document is written in two layers. **Part 1 is the plan as it stood before any
> building** — committed to git before the first discovery run, so it cannot be
> retrofitted. **Part 2** records where the plan held and where it broke; it is filled in
> as the work happens. If Part 1 and Part 2 agree everywhere, one of them is lying. I
> expect them to diverge, and the divergence is the point.

---

## Part 1 — The plan, before building

### 1.1 What I think is actually being tested

The deliverables (50 records, a pipeline, a RAG, a live URL) are the floor. The thing being
graded is judgment: whether I can tell "I couldn't find it with the method I tried" apart
from "it isn't public," whether my validation changes what ships or merely measures it, and
whether I discover the market or just copy one source's view of it at scale.

Two failure modes are called out hard enough that I am treating them as the primary risks to
design against, before I think about anything else:

1. **Single-source discovery.** If most firms come from one convenient list, no amount of
   downstream verification saves the file. This is an automatic non-advance. So discovery
   breadth is a *first-class* design constraint, not a nice-to-have.
2. **Misclassification and fake confidence.** A multi-family office or wealth manager
   relabeled as a single-family office, or a pattern-guessed email dressed as "verified,"
   costs more than an honest blank. So the schema must be able to say "undetermined" and
   "unresolved" as first-class values, and validation must be able to *delete* a value it
   cannot stand behind.

### 1.2 The one belief this whole plan rests on

**Single-family offices are the prize, and they are the hard part.** MFOs market themselves;
they will fall out of almost any source. SFOs have no reason to be visible. If my file ends
up MFO-heavy, I will have built the easy file, and the easy file fails. So I am biasing
sourcing *toward* the places SFOs are forced to become visible even when they don't want to
be — chiefly **regulatory filings** — rather than the places firms choose to advertise.

### 1.3 Splitting the two jobs: discovery vs. proof

I am keeping these separate in the schema from row one, because the instructions are explicit
that a source good for one is often useless for the other.

- **Discovery sources** answer "does this firm exist and might it be an FO?" They can be
  noisy. Their only job is to widen the candidate pool.
- **Proof sources** answer "what is this firm, who runs it now, how do I reach them?" They
  must be authoritative. A firm is not counted until a proof source backs it.

Every candidate row records *which source class discovered it*, separately from the sources
that later proved its facts. This lets me measure my own single-source risk quantitatively
before submission (target: no single discovery source class exceeds ~35% of the final 50).

### 1.4 Source classes I expect to use, and the job I expect each to do

| Source class | Region | Expected job | My prior confidence |
|---|---|---|---|
| **SEC IAPD / Form ADV** (esp. family-office-exemption filers, exempt reporting advisers) | US | Discovery **and** proof. ADV self-identifies FOs, lists AUM, executives (Sched. A), and often a contact email/phone. | High — this is my anchor source |
| **UK Companies House** (family investment companies, SIC 64/70 + name patterns) | UK | Discovery + officer names + registered address. Weak on email. | Medium |
| **Singapore (MAS directory / ACRA), other APAC/EU registries** | Global | Discovery of non-US SFOs (Singapore is a known SFO hub post-13O/13U). | Low-medium, expect friction |
| **Reputable press & rich-lists** (FT, Bloomberg, Forbes, WSJ, regional) | Global | Discovery + "why now" signals + family affiliation. Never sole proof of type. | Medium |
| **Conference / event rosters** (Campden, iConnections, Opal, family-office summits) | Global | Discovery of named principals + relevance evidence. | Medium |
| **Firm websites + portfolio/co-investment trails** | Global | Proof of activity, thesis, team; reverse-discovery from deal announcements. | Medium |
| **Free-tier enrichment** (Apollo/Hunter/RocketReach/Prospeo/Clay free credits) | Global | Principal contact discovery only, labeled "provider-returned." | Low-medium — rationed credits |

I am **deliberately not** relying on any single aggregated "family office list," because that
is precisely the copy-at-scale trap.

### 1.5 The hardest problem, named up front: verified individual emails under a free-only budget

I have no paid enrichment and no paid verifier. I cannot manufacture email confidence, and I
will not try. Deliverability ≠ ownership; a guessed `first.last@firm.com` that pings valid is
still disqualified. My legitimate paths, in priority order:

1. **Published individual emails** — the strongest free evidence, because publication *is*
   the attestation. Form ADV cover pages, firm team pages, conference bios, press.
2. **Free-tier provider returns** — labeled "returned by provider," lower confidence than
   published-and-attested.
3. **Honest "unresolved"** — with documented attempts, when 1 and 2 fail.

**My prediction (to be checked):** full contact completeness will be the scarcest resource in
the file. I expect a *minority* of the 50 to reach verified-individual-email, a larger share
to reach principal + LinkedIn with an honestly-labeled email gap, and I will fight hardest to
lift the completeness rate on SFOs specifically, since those cells carry the most value. A
file of mostly-blanks is candid but unsellable; a file of fake-confident emails is
disqualifying. The target is the honest middle, pushed as high as free tooling allows.

### 1.6 My inclusion standard (Rule 2 — the firm itself)

A candidate becomes one of the 50 **only if** all of these hold:

1. **Affirmative FO evidence** meeting the bar in §1.7 — not mere association with an
   FO-flavored source, not "family" in the name, not "serves wealthy clients."
2. **Resolved identity** — a legal/common name plus a verified domain or registered address.
3. **A type decision on record** — `SFO`, `MFO`, or `Undetermined`, each with the evidence
   that produced it. `Undetermined` is an honest, allowed outcome; guessing is not.
4. **At least a named, currently-relevant principal**, *or* a documented unresolved-principal
   note with the attempts behind it.

Secondary cells (email, phone, thesis, AUM, signals) may be honest blanks and the record
still qualifies. The firm may not be uncertain; a cell may.

### 1.7 Evidence bar for "this is a family office"

- **Strong (any one qualifies the firm):**
  - Self-identifies as a family office on its own site or in a filing;
  - Files with SEC relying on the family office exemption (rule 202(a)(11)(G)-1) — this is a
    near-definitional signal of a *single*-family office;
  - Reputable press explicitly names it as the family office of a specific family;
  - Regulatory registration/notice as a family office.
- **Corroborating (need ≥2 together):** managing a specifically-named family's wealth; no
  external client solicitation; named for a family *and* evidenced investment operations;
  listed in a credible FO directory *plus* one independent confirmation.
- **Not evidence:** family-sounding name alone; general HNW wealth management; appearing in a
  source that merely associates with family offices.

### 1.8 Type taxonomy

- **SFO** — serves one family. Signals: family-office-exemption filing; press "the family
  office of X"; no external client base.
- **MFO** — serves several families; markets services; RIA with a client base and published
  offering. Valued, but common; not to be dressed up as SFO.
- **Undetermined** — evidence insufficient to separate the two. Labeled as such, openly.

### 1.9 Email status vocabulary and the release rule

Allowed statuses: `verified` · `returned-by-provider` · `catch-all` · `unverified` ·
`unresolved` · `invalid` · `undeliverable`. Rules:

- Status is **never upgraded**. "Verified" requires attestation that *this address belongs to
  this person* (published by firm/principal, in a filing, or returned from a provider's own
  data) — not a syntax pass, not a format guess, not an AI suggestion.
- Generic/shared mailboxes (`info@`, `contact@`, `investments@`, `ir@`, `press@`, …) never
  qualify as an individual principal contact, regardless of difficulty.
- **Release-gating:** `invalid` and `undeliverable` values are removed from the
  customer-facing cell and retained only in `data/audit/`. A validation step that finds a
  problem and ships the value anyway is measurement, not validation.

### 1.10 Anticipated blind spots (before I start)

- **Non-US SFOs** will be under-represented relative to US, because US filings are uniquely
  rich and free. I expect to have to work to keep the file from becoming US-centric, and I
  may not fully succeed — I will report the residual skew rather than hide it.
- **Free-tier email ceilings** will cap completeness; the skew will land hardest on the most
  private SFOs, i.e. exactly the highest-value records.
- **Recency of signals** is effort-intensive per record; a thin-signal file reads as static
  intelligence with lower value. I need to budget real time for dated signals, not treat
  them as an afterthought.

### 1.11 What "good" looks like at submission

Not perfection. A file where: discovery is provably multi-source; every firm clears the FO
bar or isn't in the file; types are honest with `Undetermined` used where earned; a real and
growing share of records carry a named decision-maker with LinkedIn and an attested email;
every high-value cell carries its basis; and the RAG answers only what the records support
and says so plainly when they don't.

---

## Part 2 — Where the plan held and where it broke

*(Filled in during the build. Each entry dated, tied to the research log.)*

**[2026-07-28] Broke: "SEC Form ADV is the anchor" (§1.4).** I planned to anchor on ADV /
family-office-exemption filers. First contact broke this on two counts: ADV isn't in
EDGAR's full-text index (0 hits), and — the deeper error — SFOs that *use* the family-office
exemption file no ADV at all, so the exemption I named as my best SFO signal actually
guarantees the record is missing from ADV. The assumption was backwards.

**[2026-07-28] Held, and better than expected: 13F-HR as the SFO vein (§1.2 belief).** My
core belief was that SFOs are forced visible chiefly through regulation. That held — but the
mechanism was Form 13F, not ADV. 893 13F filings mention "family office"; a first sample of
~120 filings yielded 29 self-identified family-office filers including real SFOs
(Duquesne/Druckenmiller, Louis-Dreyfus). 13F also hands me holdings as dated signals for
free. Net: the belief survived, the named source did not — so ADV is demoted and 13F becomes
the US anchor, with the explicit caveat that 13F misses SFOs filing under non-obvious names
(Cascade, Bezos Expeditions), which I now owe to a separate reverse-discovery angle.

**[2026-07-28→29] The SFO/MFO reality, and how the file's shape emerged.** Enrichment (via
research agents returning strictly-sourced JSON, gated by `ingest_research.py`) confirmed the
prediction in §1.5: "X Family Office" 13F filers are mostly *registered multi-family offices*,
not SFOs; genuine unregistered SFOs are rare in that vein. So the SFO count had to come from a
different mechanism — press/known-individual discovery (Cascade, Bezos, Dell, Soros, Bloomberg,
LEGO, L'Oréal, Chanel…) and a Singapore/APAC registry-and-press pass (Dyson, Dalio, UOB, Nippon
Paint…). Net final composition: 50 records across **four independent discovery classes**
(sec-13f 17 · press 17 · uk 8 · apac 8; max 34%), **34 SFO / 15 MFO / 1 Undetermined**, 10
countries.

**[2026-07-28→29] Constraints that shaped the method, honestly.** Two forces bent the plan:
(1) a free-only budget with no paid enrichment/verifier, and (2) repeated usage-limit throttling
that killed model-based research agents mid-run. The response was to lean on **deterministic,
non-model enrichment via direct government APIs** (SEC 13F signature blocks, SEC IAPD adviser
registration, UK Companies House SIC + officers + PSC) — none of which consumes model budget —
for classification, phones, and firm proof, reserving scarce model calls for the judgement-heavy
work (principal identification, published-email discovery). A recursive agent-delegation failure
(agents spawning agents, ~250k tokens for zero output) is logged in the research log as a real
cost and lesson.

**[2026-07-29] Contact strategy, and the email asymmetry.** A review flagged that every verified
email sat on an MFO. That is structural, not a defect — SFOs don't publish individual emails, and
fabricating one is disqualifying. Rather than shrug, we maximised the *other* legitimate SFO
channels: verified firm **phones** from 13F signature blocks, and a **LinkedIn pass that replaced
billionaire figureheads with the reachable investment executives** (Cascade→Larson, Soros→
Fitzpatrick, Willett→Rattner, Dell→Lemkau, Weybourne→Simpson…). SFO reachability rose from ~12 to
27 of 34; overall 43/50 carry a direct channel; every record carries a named principal + dated
2026 signals.

**[2026-07-29] RAG, and testing the answer layer.** Built keyless retrieval (structured + lexical,
validated in `rag/prototype.py`) + a free-OpenRouter grounded answer layer with a sufficiency gate
and an extractive fallback that cannot hallucinate. Live-testing the deployed system caught real
bugs — a deprecated free-model slug (fixed with a fallback list), an entity-name boost that broke
the decline gate on generic words, a markdown-table format the UI mis-rendered — all fixed and
re-verified against the live URL (see `rag/app/README.md`).

### Part 2 — Material blind spots that remain (stated, not hidden)
- **Contact completeness is uneven.** 7/50 verified individual emails; 43/50 have *some* channel.
  The prestigious private SFOs (Bezos, Tethys/Bettencourt, Dyson, several Singapore) carry a named
  principal + signals but no direct contact — honest, documented gaps, not fabricated fills.
- **US-weighting.** 26/50 US. The global slice is real (UK/Europe/Asia/Australia/Canada) but the
  US is over-represented because SEC filings are uniquely rich and free.
- **13F equity values are floors,** not total AUM, and are labelled as such; some AUM cells are
  press estimates with dates.
- **Some principal LinkedIn matches are "unconfirmed"** (Bayshore, Bezos) and labelled so; a couple
  of phones are sourced from older filings (Willett's 2014 13F) and flagged.
- **A larger discovered pool (71 qualified) exceeds the 50** under the source cap; 21 qualified
  records sit in reserve rather than being forced in past the single-source ceiling.
- **Free-only tooling caps email verification** at "published/attested" — no paid enrichment means
  no provider-returned coverage for the harder SFOs.
- **RAG answer latency.** The live answer layer runs on a **free** OpenRouter model that queues
  for ~10–30s. This is a deliberate cost trade-off (no paid key): we wait for the LLM-grounded
  answer rather than downgrade to the extractive fallback, and the UI states the expected wait.
  A paid/faster model key (`OPENROUTER_MODEL`) drops responses to 1–3s with no code change.

---

## Part 3 — Summary (direct answers to the brief's checklist)

### 3.1 How the system found the records (discovery)
Four independent discovery source classes, deliberately different mechanisms so no one blind
spot dominates (final mix 17 sec-13f · 17 press · 8 uk · 8 apac, max 34%):
- **SEC EDGAR 13F-HR full-text search** — programmatic; distinct 13F filers whose documents
  mention "family office" (`pipeline/discovery/sec_13f.py`).
- **UK Companies House advanced search** — active companies by family-office name patterns
  (`pipeline/discovery/uk_companies_house.py`).
- **Press / known-UHNW-individual reverse-discovery** — for hidden-name SFOs that phrase-search
  structurally misses (Cascade, Bezos, Dell, Soros, LEGO, L'Oréal…), each confirmed against a
  primary source.
- **Singapore / APAC registry + press** — the 13O/13U hub (Dyson, Dalio, UOB, Nippon Paint…).

### 3.2 How it enriched them (entity / principal / signal)
- **Entity:** type, thesis, sectors, AUM, corporate LinkedIn, HQ — from firm sites, SEC filings,
  Companies House SIC, and press.
- **Principal:** the *reachable* investment decision-maker (CIO/CEO, not the figurehead), current
  title, individual `/in/` LinkedIn.
- **Signal:** dated 2026 activity (13F holdings, hires, deals, news).
- **Method split:** deterministic government-API enrichment (13F signature blocks, IAPD adviser
  registration, Companies House officers/PSC, published-email harvesting) carried classification,
  phones, and firm proof at zero model cost; research agents (held to a strict sourced-JSON
  no-fabrication contract) carried the judgement-heavy principal/email work.

### 3.3 How I validated the AI's output
Validation *changes what ships*, it does not merely measure:
1. **No-fabrication ingest gate** (`ingest_research.py`): drops generic mailboxes, rejects any
   LinkedIn that isn't an individual `/in/` profile, and downgrades a "verified" email that has
   no source URL.
2. **Email re-verification at source** (`pipeline/validation/validate.py`): re-fetches each
   email's cited page and only keeps `verified` if the address literally appears there;
   fetched-but-absent → downgraded; `invalid`/`undeliverable` → removed to the audit sheet.
3. **Firm-proof qualification (Rule 2):** only firms with affirmative FO evidence qualify;
   disproven ones (e.g. "Family Office Research LLC" = branding-only wealth manager; 22 banks
   that matched "family office" only in holdings text) are rejected to the audit record.
4. **Independent manual spot-checks:** I personally re-fetched sample emails (Callan, Custos,
   CVA, Pioneer) and confirmed them at source; caught a bad auto-match (`timonier@timonier.com`).
5. **Answer-layer validation (the RAG):** live queries confirm the deployed system answers only
   from the records and **declines** on off-topic and thin-evidence queries — both layers tested,
   not just the data.

### 3.4 Which source classes supported which kinds of claims
| Source class | Claims it was trusted for | Claims it was NOT trusted for |
|---|---|---|
| **SEC 13F-HR** | firm existence, legal name, HQ address, AUM floor (equities), dated holdings signals, firm phone + signatory (signature block) | SFO/MFO type on its own; individual emails |
| **SEC IAPD (adviser reg.)** | SFO-vs-MFO signal (registered→serves clients; absent→family-office exemption), CRD/SEC#, verified office address | contacts; recent signals |
| **UK Companies House** | firm existence, registered address, SIC activity class, officers/directors, **PSC → controlling family (SFO proof)** | emails; investment thesis |
| **Reputable press** | SFO identification, family affiliation, "why-now" signals, AUM estimates (dated) | sole proof of type without corroboration; contacts |
| **Firm websites / team pages** | **published individual emails**, principal titles, thesis/description | firm existence proof on its own |
| **LinkedIn (search snippets)** | individual `/in/` profile + reachable-principal identity | anything unverifiable (profiles aren't fetchable — matched via snippet) |

### 3.5 Material blind spots that remained
See the "Material blind spots that remain" section above (contact-completeness unevenness,
US-weighting, floor-not-total AUM, a few unconfirmed LinkedIn / dated phones, reserve pool beyond
50, free-tier verification ceiling, RAG latency).
