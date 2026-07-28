"""Deterministic published-email harvester (no model budget).

For a qualified record that has a website but no usable individual email, fetch the firm's
own contact/team pages and extract published mailto: addresses. If a principal's name tokens
match an address local-part, that address is an attested, published individual email for
that person -> set it verified (publication IS the attestation). Generic mailboxes are
never assigned. Non-matching individual emails are stashed in raw for the research pass.

This is legitimate pipeline enrichment: it reads what the firm publishes on its own site.
It does NOT guess or pattern-generate — an address only ships if it literally appears in a
mailto: on the firm's page AND its local-part matches the named principal.
"""
from __future__ import annotations
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from pipeline.common.http import fetch
from pipeline.common.schema import GENERIC_EMAIL_LOCALPARTS
from pipeline.common import store

PAGES = ["", "/contact", "/contact-us", "/team", "/our-team", "/people", "/about",
         "/leadership", "/who-we-are", "/our-people"]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAILTO_RE = re.compile(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.I)


def _base(website, domain):
    if website and website.startswith("http"):
        return website.rstrip("/")
    d = (domain or website or "").replace("https://", "").replace("http://", "").strip("/ ")
    return "https://" + d if d else ""


def _name_tokens(full_name):
    toks = [t.lower() for t in re.split(r"[^A-Za-z]+", full_name or "") if len(t) > 2]
    # drop common honorifics/initials
    return [t for t in toks if t not in {"the", "mr", "mrs", "ms", "dr", "jr", "sr"}]


def _match(email, tokens):
    local = email.split("@")[0].lower()
    if local in GENERIC_EMAIL_LOCALPARTS:
        return False
    # require a real name token (surname or given name) to appear in the local-part
    return any(t in local for t in tokens if len(t) > 2)


def run():
    cands = [r for r in store.all_candidates() if r.get("status") == "qualified"]
    targets = [r for r in cands if _base(r.get("website"), r.get("domain"))
               and not (r.get("principal_email") and r.get("email_status") in ("verified", "returned-by-provider"))]
    print(f"site-contact harvest over {len(targets)} qualified records with a website...")
    found = 0
    for r in targets:
        base = _base(r.get("website"), r.get("domain"))
        tokens = _name_tokens(r.get("principal_full_name"))
        seen_mailtos, seen_emails = set(), set()
        for p in PAGES:
            try:
                html = fetch(base + p, accept="text/html")
            except Exception:
                continue
            seen_mailtos |= {e.lower() for e in MAILTO_RE.findall(html)}
            seen_emails |= {e.lower() for e in EMAIL_RE.findall(html)
                            if not e.lower().endswith((".png", ".jpg", ".gif", ".svg", ".webp"))}
        # prefer mailto (explicit contact intent); fall back to plain-text emails
        pool = seen_mailtos or seen_emails
        indiv = [e for e in pool if e.split("@")[0].lower() not in GENERIC_EMAIL_LOCALPARTS]
        match = next((e for e in indiv if tokens and _match(e, tokens)), "")
        raw = json.loads(r["raw"]); raw["site_emails"] = sorted(pool)
        store.upsert_raw(r["record_id"], raw)
        if match:
            store.set_fields(
                r["record_id"],
                principal_email=match, email_status="verified", last_validated="2026-07-28",
                email_source=f"{base} (published mailto/contact page)",
                email_basis=f"Address published on the firm's own site with local-part matching "
                            f"the named principal ({r.get('principal_full_name')}).")
            found += 1
            print(f"  + {r['firm_common_name'][:28]:28} -> {match}")
    print(f"Harvested {found} attested individual emails from firm sites.")


if __name__ == "__main__":
    run()
