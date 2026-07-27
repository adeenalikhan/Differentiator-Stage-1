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

- _pending first discovery run_
