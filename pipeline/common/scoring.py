"""Qualification (Rule 2 — the firm) and completeness tiering (per-record value).

These are separate on purpose, mirroring the assessment's two rules:
  * qualify_firm(): is there affirmative evidence the FIRM is a family office? A firm that
    fails this does not count toward the 50, no matter how good its other cells are.
  * completeness_tier(): how actionable is the record for a customer today? Drives value,
    not qualification. A qualified firm may still be a low tier with honest blanks.
"""
from __future__ import annotations

STRONG = {"strong", "corroborated"}


def qualify_firm(rec: dict) -> tuple[bool, str]:
    """Return (qualifies, reason). Firm-level proof, stricter than any cell."""
    proof = (rec.get("fo_proof_strength") or "").strip().lower()
    fo_ev = (rec.get("is_fo_evidence") or "").strip()
    fo_type = (rec.get("fo_type") or "").strip()
    if proof == "insufficient":
        return False, "fo_proof_strength=insufficient (no affirmative FO evidence)"
    if proof not in STRONG:
        return False, f"fo_proof_strength not established ('{proof or 'blank'}')"
    if not fo_ev:
        return False, "no is_fo_evidence recorded"
    if not fo_type or fo_type == "Undetermined":
        # Undetermined TYPE is allowed on a qualified firm ONLY if FO-hood itself is proven.
        # We keep it, but flag; the firm still qualifies as a family office of unknown subtype.
        return True, "qualifies as family office; subtype Undetermined (honest)"
    return True, f"qualifies ({fo_type}, {proof})"


def completeness_tier(rec: dict) -> str:
    """A = full contact (principal + /in/ LinkedIn + attested email); B = principal + one of
    LinkedIn/phone; C = firm-level only. Signals add a '+' marker."""
    has_principal = bool(rec.get("principal_full_name"))
    has_li = bool(rec.get("principal_linkedin"))
    email_ok = (rec.get("email_status") or "") in {"verified", "returned-by-provider", "catch-all"} \
        and bool(rec.get("principal_email"))
    has_phone = bool(rec.get("principal_phone"))
    has_signal = bool(rec.get("signals"))

    if has_principal and has_li and email_ok:
        tier = "A"
    elif has_principal and (has_li or has_phone or email_ok):
        tier = "B"
    else:
        tier = "C"
    return tier + ("+" if has_signal else "")
