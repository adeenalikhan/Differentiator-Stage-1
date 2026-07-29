# Three full validation chains

Three records traced end to end: discovery source → extraction method → enrichment steps →
validation logic → confidence assessment → exact sources. Chosen to span the range: a
single-family office with an honest contact gap, a multi-family office with a source-verified
email, and a press-discovered SFO where we substituted the reachable executive for the
billionaire figurehead. All values reconcile with `data/final/family_office_dataset.xlsx`.

---

## 1. Duquesne Family Office LLC — SFO (SEC 13F) — honest email gap

- **Discovery source (found here):** SEC EDGAR full-text search for the phrase "family office"
  in Form 13F-HR (`efts.sec.gov/LATEST/search-index`). Duquesne appeared as a distinct 13F
  filer, CIK 0001536411. Discovery class: `sec-13f`.
- **Extraction method:** `pipeline/enrichment/sec_13f_traverse.py` fetched the filing's
  `primary_doc.xml` and information table → verified legal name, New York HQ, signatory
  (Sue Meng, GC), portfolio value + position count + report quarter, and top holdings.
- **Enrichment steps:**
  - *Entity/type:* `pipeline/enrichment/sec_iapd.py` found **no** SEC investment-adviser
    registration for Duquesne. Filing a 13F (>$100M) while unregistered is only lawful under
    the single-family-office exemption (rule 202(a)(11)(G)-1) → strong SFO signal. Corroborated
    by press uniformly describing it as Stanley Druckenmiller's family office.
  - *Principal:* Stanley Druckenmiller, Chairman/CEO/CIO — he is himself the active PM, so no
    figurehead substitution needed. The 13F signatory (GC Sue Meng) is recorded as a secondary
    verified contact, not upgraded to "principal."
  - *AUM:* stated as a **floor** — "13F US-listed equities ~$4.06B (Q3 2025)… a FLOOR, not
    total AUM" — never asserted as total AUM.
  - *Signals:* dated Q1/Q3/Q4 2025 13F portfolio changes.
  - *Contact:* firm phone **212-830-6500** from the 13F signature block. Email: searched for a
    firm website/team page (none — Duquesne has no public site) and any published individual
    address; none found → `email_status = unresolved` with documented attempts.
- **Validation logic:** firm qualifies under Rule 2 (unregistered 13F filer + press = family
  office, `fo_proof_strength = strong`). Email left honestly blank rather than guessed. Phone
  re-traceable to the filing URL.
- **Confidence:** firm HIGH; type SFO HIGH; principal HIGH; phone HIGH (SEC filing); email
  UNRESOLVED (honest). Tier **B+**.
- **Exact sources:**
  - Filing: `https://www.sec.gov/Archives/edgar/data/1536411/000153641126000004/primary_doc.xml`
  - `https://13f.info/manager/0001536411-duquesne-family-office-llc`
  - `https://www.fool.com/investing/how-to-invest/famous-investors/duquesne-family-office`
  - `https://www.institutionalinvestor.com/article/stan-druckenmiller-overhauls-his-family-offices-us-stock-portfolio`

---

## 2. Callan Family Office, LLC — MFO (SEC 13F) — email verified at source

- **Discovery source:** same SEC 13F full-text vein (CIK 0001938970). Class: `sec-13f`.
- **Extraction method:** 13F `primary_doc.xml` traversal → HQ (Radnor, PA), signatory John
  Ginter, phone 267-250-2036, portfolio signals.
- **Enrichment steps:**
  - *Type:* IAPD shows a **registered** investment adviser with a UHNW client base ($50M-min,
    ~$5B AUM); RIABiz/Forbes cover it as a **multi-family office** → `MFO` (not dressed up as
    SFO despite the "family office" name).
  - *Principal:* Jack (John) Ginter, CEO & Founding Partner — the 13F signatory "John Ginter"
    and the site's "Jack Ginter" are the same person (noted in caveats).
  - *Contact — the key step:* the firm's own team page publishes his individual email. A
    research agent reported `jginter@callanfo.com` (source URL cited); the **release-gating
    validator** (`pipeline/validation/validate.py`) then **re-fetched that URL and confirmed
    the address literally appears on the page** → `email_status = verified`, `last_validated`
    set. LinkedIn `/in/` profile confirmed (name+firm+role match).
- **Validation logic:** email is `verified` only because a second, independent re-fetch found
  it published at the cited source — not because a tool called it deliverable. Note the mail
  domain (`callanfo.com`) differs from the web domain (`callanfamilyoffice.com`), recorded in
  provenance.
- **Confidence:** firm HIGH; type MFO HIGH; principal HIGH; **email VERIFIED** (re-confirmed
  at source); phone HIGH; LinkedIn confirmed. Tier **A+**.
- **Exact sources:**
  - Email: `https://callanfamilyoffice.com/team/jack-ginter/`
  - LinkedIn: `https://www.linkedin.com/in/jack-ginter-70276773/`
  - Adviser registration: `https://adviserinfo.sec.gov/firm/summary/317446` (CRD 317446, SEC# 801-122987)
  - AUM/signal: `https://riabiz.com/a/2024/4/9/an-abbot-downing-breakaway-but-not-exactly-callan-family-office-hits-5-billion-of-aum-after-just-two-years-using-a-creative-callan-brand-deal-and-a-partnership-model`

---

## 3. Willett Advisors LLC — SFO (press) — figurehead → reachable executive

- **Discovery source (found here):** press / known-UHNW-individual angle — Michael Bloomberg →
  his family office entity (Willett Advisors). Class: `press`. This is a *different discovery
  mechanism* from SEC name-search (Willett's name contains no "family office"), which is
  exactly why the multi-source approach matters.
- **Extraction method:** two-part. (1) Identity, type, principal and AUM extracted from
  reputable press + a research agent under the strict sourced-JSON contract. (2) The firm phone
  and address were pulled deterministically by `pipeline/enrichment/sec_sfo_phone.py`, which
  looked up Willett's CIK (0001509379), fetched its 13F `primary_doc.xml`, and parsed the
  signature block — the same cover parser used for the 13F set.
- **Proof (proven here):** Wikipedia + family-office trade press name Willett Advisors as
  Michael Bloomberg's family office; SEC registration corroborates the entity. `fo_type = SFO`,
  `fo_proof_strength = strong`.
- **Enrichment steps:**
  - *Principal — figurehead substitution:* the identified decision-maker is **Steven Rattner,
    Chairman & CEO of Willett** — the person a fund actually reaches — not Michael Bloomberg.
    This was a deliberate call in the LinkedIn pass: for offices fronted by a busy billionaire,
    we surface the executive who runs investments.
  - *LinkedIn:* `https://www.linkedin.com/in/srattner/` (individual `/in/`, matched to person+firm).
  - *Contact phone:* 212-205-0100 from Willett's 13F signature block.
  - *AUM:* ~$25B (press).
- **Validation logic + honesty flag:** the phone comes from Willett's 13F, but **that 13F
  ceased after Q3 2014** (last filing 2014-11-04) because most assets are now private — recorded
  in caveats, so the phone is labelled as sourced from a 2014 filing (firm main line, likely
  still valid, but dated). Email: no published individual address found → `unresolved` (honest).
- **Confidence:** firm HIGH; type SFO HIGH; principal (Rattner) HIGH; LinkedIn confirmed; phone
  MEDIUM (2014-sourced firm line, flagged); email UNRESOLVED. Tier **B+**.
- **Exact sources:** `https://en.wikipedia.org/wiki/Willett_Advisors`;
  `https://www.linkedin.com/in/srattner/`;
  13F `https://www.sec.gov/Archives/edgar/data/1509379/000114036114040025/primary_doc.xml`.

---

### What these three show together
Multi-source discovery (SEC 13F **and** press/known-individual), Rule-2 firm proof in three
different evidentiary shapes (regulatory exemption, RIA registration, press+registry), the
release gate that only marks an email `verified` after re-confirming it at source, and honest
labelling everywhere the evidence stops (unresolved emails, floor-not-total AUM, a dated phone).
