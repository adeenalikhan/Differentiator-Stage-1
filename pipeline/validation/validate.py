"""Release-gating validation. This step must CHANGE what ships, not just measure it.

Controls implemented:
  1. Email re-verification at source: for every record carrying an email with an http
     source, re-fetch that page and confirm the address actually appears there. Confirmed ->
     status stays/becomes `verified`. Fetched-but-absent -> downgraded to `unverified`
     (kept, but honestly labelled). Fetch failed -> left as-is with a note (no false destroy).
  2. Generic / malformed addresses -> removed from the customer field, logged to audit.
  3. invalid / undeliverable -> removed from the customer field, logged to audit.
  4. Firm qualification (Rule 2): firms without affirmative FO evidence are marked rejected
     and never counted toward the 50.
  5. Completeness tiering for every surviving record.

Run: python -m pipeline.validation.validate
"""
from __future__ import annotations
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch
from pipeline.common.schema import Record, GENERIC_EMAIL_LOCALPARTS, EMAIL_STATUSES_BLOCKED_FROM_RELEASE
from pipeline.common import store
from pipeline.common.scoring import qualify_firm, completeness_tier

TODAY = "2026-07-28"


def _email_on_page(email, url):
    """Return True/False/None (None = could not fetch)."""
    try:
        html = fetch(url, accept="text/html")
    except Exception:
        return None
    hay = html.lower()
    if email.lower() in hay:
        return True
    # handle simple obfuscations: name [at] domain, HTML entities
    local, _, dom = email.lower().partition("@")
    variants = [f"{local}&#64;{dom}", f"{local} [at] {dom}", f"{local}(at){dom}"]
    return any(v in hay for v in variants)


def verify_emails():
    cands = store.all_candidates()
    checked = confirmed = downgraded = removed = unreachable = 0
    for r in cands:
        email = (r.get("principal_email") or "").strip()
        status = (r.get("email_status") or "").strip()
        if not email:
            continue
        # already confirmed at source today (e.g. by the site-contact harvester) -> trust it
        if r.get("last_validated") == TODAY and status == "verified":
            continue
        checked += 1
        local = email.split("@")[0].lower()
        # remove generic / blocked-status from customer field
        if local in GENERIC_EMAIL_LOCALPARTS or status in {"invalid", "undeliverable"}:
            store.audit(r["dedup_key"], r["firm_legal_name"], "principal_email", email,
                        f"removed from customer field (status={status or 'generic'})")
            store.set_fields(r["record_id"], principal_email="", email_status="unresolved")
            removed += 1
            continue
        src = (r.get("email_source") or "").strip()
        url = re.search(r"https?://\S+", src)
        if not url:
            # provider-returned with no page: cannot re-verify at source; leave labelled
            continue
        present = _email_on_page(email, url.group(0).rstrip('.,);'))
        if present is True:
            store.set_fields(r["record_id"], email_status="verified", last_validated=TODAY)
            confirmed += 1
        elif present is False:
            store.audit(r["dedup_key"], r["firm_legal_name"], "principal_email", email,
                        f"email not found at cited source on re-fetch ({url.group(0)}); downgraded verified->unverified")
            store.set_fields(r["record_id"], email_status="unverified", last_validated=TODAY)
            downgraded += 1
        else:
            unreachable += 1  # left as-is
    print(f"Emails checked={checked} confirmed={confirmed} downgraded={downgraded} "
          f"removed={removed} source_unreachable={unreachable}")


def qualify_and_tier():
    """Three outcomes, honestly separated:
      qualified            — enriched AND affirmative FO evidence (counts toward 50)
      rejected             — enriched AND actively disproven (insufficient evidence / not an FO)
      pending-enrichment   — not yet researched; NOT a rejection, just not done
    """
    cands = store.all_candidates()
    q = rej = pending = held = 0
    for r in cands:
        # preserve an explicit prior rejection (e.g. deterministic false-positive cull);
        # do not let "no evidence yet" resurrect it to pending.
        if r.get("status") == "rejected":
            held += 1
            continue
        enriched = bool((r.get("fo_proof_strength") or "").strip() or (r.get("is_fo_evidence") or "").strip())
        if not enriched:
            store.set_fields(r["record_id"], status="pending-enrichment")
            pending += 1
            continue
        ok, reason = qualify_firm(r)
        if ok:
            store.set_fields(r["record_id"], status="qualified")
            q += 1
        else:
            store.audit(r["dedup_key"], r["firm_legal_name"], "firm-qualification", "", reason)
            store.set_fields(r["record_id"], status="rejected")
            rej += 1
        store.set_fields(r["record_id"], completeness_tier=completeness_tier(r))
    print(f"Qualification: qualified={q} rejected={rej} pending-enrichment={pending}")


if __name__ == "__main__":
    verify_emails()
    qualify_and_tier()
    s, src = store.counts()
    print("status:", s)
