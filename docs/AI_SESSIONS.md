# AI working sessions

**Scope statement (required by the brief).** The AI session record for this assessment begins
with the **first interaction with any AI model about this assessment** — the opening message of
this Claude Code session, in which the "How We Work" diagram and the Task 1 brief were shared —
and includes **all material AI sessions** used for the work. There were no earlier AI sessions
on this assessment (confirmed at the outset). This project was built end-to-end in a single
Claude Code session; the research/enrichment subagents were spawned from within it and their
transcripts are part of the same session tree.

**Raw record.** The primary raw record is the full export of this Claude Code conversation
(including tool calls, subagent spawns, and their returned results). Attach that export / share
link with the submission. The subagents' own transcripts are saved by the harness under the
session's task directory and are referenced from the conversation at the points they were
launched.

---

## Key prompts given to AI models (templates, quoted)

Per-run prompts appear verbatim in the conversation transcript at the point each agent was
launched; the reusable templates are reproduced here. Every research agent was held to the same
no-fabrication contract.

### Discovery + enrichment agent (research → strict JSON)
> "You are a due-diligence researcher for a COMMERCIAL family-office dataset. Accuracy and honest
> sourcing beat completeness; a guessed value is worse than an honest blank. … For EACH firm
> output a JSON object with EXACTLY these keys: record_id, firm_legal_name, website, fo_type
> ('SFO'|'MFO'|'Undetermined'), fo_type_evidence, is_fo_evidence, fo_proof_strength, …,
> principal_full_name, principal_title, principal_linkedin, principal_linkedin_status,
> principal_email, email_status, email_source, email_basis, … signals, signals_dates,
> signals_source, caveats, sources_checked.
> RULES: … principal_linkedin MUST be a personal /in/ profile matching person+firm+current role,
> else ''. principal_email: ONLY a real PUBLISHED individual email (firm team/bio page, filing,
> press) — exact URL in email_source, quoted context in email_basis. NEVER pattern-generate (no
> name@domain guessing). Generic mailboxes (info@, contact@) don't count. ZoomInfo/RocketReach/
> Apollo masked/broker addresses do NOT count — exclude them. If none published: email='',
> email_status='unresolved', list attempts. Cite a URL for every non-empty fact; inferences/
> speculation ONLY in caveats."

Plus the hard operational instruction added after a delegation failure:
> "CRITICAL: Do ALL research YOURSELF with your own WebSearch/WebFetch tools, one firm at a time.
> Do NOT use the Agent or Task tool. Do NOT spawn, delegate to, or wait on any sub-agents."

### Hidden-name SFO discovery agent
> "The most valuable records are genuine SINGLE-FAMILY OFFICES … they hide: often no website,
> neutral names (Cascade = Gates; Bezos Expeditions = Bezos). DISCOVER ~10-12 real SFOs through
> SEVERAL independent angles and CONFIRM each against a primary source (press naming it as family
> X's office, a 13F filing, a registry). A family-sounding name is NOT enough … Most true SFOs
> will have NO published email — an honest blank on a high-value SFO is expected and valued."

### LinkedIn / reachable-principal pass
> "Find the individual LinkedIn profile (/in/…) of the person a fund manager would actually
> contact. For a family office fronted by a busy billionaire (Gates, Bezos, Bloomberg, Soros),
> the reachable decision-maker is usually the office's CIO/CEO/Managing Director, NOT the
> figurehead — identify and return that professional … principal_email: ONLY a real PUBLISHED
> individual email … NEVER pattern-generate."

The full, exact, per-run versions of these (with the specific firm lists) are in the transcript.
