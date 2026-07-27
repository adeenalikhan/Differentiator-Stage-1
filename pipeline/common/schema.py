"""Single source of truth for the record schema.

Design principles baked into the schema:
  * Discovery is separated from proof (see `discovery_*` vs the proof/evidence fields).
  * Every high-value cell has a companion basis/source/status so a value can carry its
    evidence, and so validation can *downgrade or delete* a value it cannot stand behind.
  * "Undetermined" (firm type) and "unresolved" (contact) are first-class, honest values.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class FOType(str, Enum):
    SFO = "SFO"                 # single-family office
    MFO = "MFO"                 # multi-family office
    UNDETERMINED = "Undetermined"


class EmailStatus(str, Enum):
    VERIFIED = "verified"                 # attested to belong to this person
    PROVIDER = "returned-by-provider"     # from an enrichment provider's own data
    CATCH_ALL = "catch-all"               # domain accepts all; lower confidence
    UNVERIFIED = "unverified"             # present but not attested
    UNRESOLVED = "unresolved"             # not found after documented attempts
    INVALID = "invalid"                   # fails syntax/structure -> audit only
    UNDELIVERABLE = "undeliverable"       # mailbox does not exist -> audit only


class LinkedInStatus(str, Enum):
    CONFIRMED = "confirmed"       # /in/ profile, name+org+role match the record
    UNCONFIRMED = "unconfirmed"   # a candidate profile, not yet matched
    UNRESOLVED = "unresolved"     # none found after documented attempts


# Statuses whose values must NOT appear in the customer-facing contact cell.
EMAIL_STATUSES_BLOCKED_FROM_RELEASE = {EmailStatus.INVALID, EmailStatus.UNDELIVERABLE}

# Generic / shared mailbox local-parts that never qualify as an individual contact.
GENERIC_EMAIL_LOCALPARTS = {
    "info", "contact", "admin", "office", "support", "hello", "inquiries",
    "inquiry", "investments", "investors", "investorrelations", "ir", "media",
    "press", "team", "reception", "general", "enquiries", "hi", "mail", "email",
}

# Discovery source *classes* — used to measure single-source concentration.
DISCOVERY_SOURCE_CLASSES = [
    "sec-adv",            # SEC IAPD / Form ADV
    "uk-companies-house",
    "apac-eu-registry",   # MAS/ACRA/other non-US registries
    "press",              # reputable press / rich-lists
    "conference",         # event/conference rosters
    "portfolio-trail",    # reverse-discovery from deals / portfolio pages
    "directory",          # public directory (only with independent corroboration)
]


@dataclass
class Record:
    # --- identity & provenance -------------------------------------------------
    record_id: str = ""
    firm_legal_name: str = ""
    firm_common_name: str = ""

    discovery_source_class: str = ""      # one of DISCOVERY_SOURCE_CLASSES
    discovery_source_detail: str = ""     # exact source (e.g. specific filing / URL)
    discovery_url: str = ""

    # --- what the firm IS (Rule 2: firm must be proven) ------------------------
    fo_type: str = FOType.UNDETERMINED.value
    fo_type_evidence: str = ""            # why we assigned this type
    is_fo_evidence: str = ""              # the affirmative proof it is a family office
    fo_proof_strength: str = ""           # "strong" | "corroborated" | "insufficient"
    family_affiliation: str = ""

    # --- entity enrichment -----------------------------------------------------
    website: str = ""
    domain: str = ""
    url_quality: str = ""
    corporate_linkedin: str = ""
    description: str = ""
    investment_thesis: str = ""
    investing_sectors: str = ""
    aum: str = ""
    aum_basis: str = ""                   # source + as-of date
    hq_street: str = ""
    hq_city: str = ""
    hq_region: str = ""
    hq_country: str = ""

    # --- principal & contact ---------------------------------------------------
    principal_full_name: str = ""
    principal_title: str = ""
    principal_relevance: str = ""         # evidence they are a CURRENT decision-maker
    principal_linkedin: str = ""
    principal_linkedin_status: str = LinkedInStatus.UNRESOLVED.value
    principal_email: str = ""
    email_status: str = EmailStatus.UNRESOLVED.value
    email_source: str = ""                # where it came from
    email_basis: str = ""                 # how ownership was attested
    principal_phone: str = ""
    phone_source: str = ""

    # --- signals (why now) -----------------------------------------------------
    signals: str = ""                     # recent investments/hires/news
    signals_dates: str = ""
    signals_source: str = ""

    # --- meta ------------------------------------------------------------------
    completeness_tier: str = ""           # computed: see scoring
    caveats: str = ""                     # honest notes on what is uncertain/missing
    last_validated: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# Columns a customer actually reads (the "Dataset" sheet).
CUSTOMER_FACING_FIELDS = [
    "record_id", "firm_common_name", "fo_type", "family_affiliation",
    "website", "corporate_linkedin", "description", "investment_thesis",
    "investing_sectors", "aum", "hq_city", "hq_region", "hq_country",
    "principal_full_name", "principal_title", "principal_linkedin",
    "principal_email", "email_status", "principal_phone",
    "signals", "signals_dates", "completeness_tier", "caveats",
]

# Columns that carry the basis/verification for high-value cells (the "Provenance" sheet).
PROVENANCE_FIELDS = [
    "record_id", "firm_legal_name", "discovery_source_class", "discovery_source_detail",
    "discovery_url", "fo_type_evidence", "is_fo_evidence", "fo_proof_strength",
    "aum_basis", "principal_relevance", "principal_linkedin_status",
    "email_source", "email_basis", "phone_source", "signals_source", "last_validated",
]
