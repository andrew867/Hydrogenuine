"""Public Claim Checker v2 — enhanced claim validation against known
patterns.

The checker is NOT authority. It is a guard. A claim passing the checker
does NOT make it true. Plausible is NOT true. Passing a check is NOT
proof. Promotion is NEVER allowed.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from hg_runtime.output_quality.rules import (
    detect_unsafe_overclaim,
    detect_fake_falsification,
    detect_generic_slop,
)

SCHEMA_VERSION = "public_claim_checker_v2"

CLAIM_STATUSES = {
    "unchecked",
    "plausible",
    "implausible",
    "overclaim",
    "unsupported",
    "needs_source",
    "needs_review",
}

_INVARIANTS = {
    "checker_is_not_authority": True,
    "plausible_is_not_true": True,
    "passing_check_is_not_proof": True,
    "promotion_allowed": False,
    "model_output_treated_as_truth": False,
}

# Statuses that require operator review
_REVIEW_STATUSES = {"overclaim", "implausible", "needs_review", "unsupported"}

# Statuses that are unsafe for display
_UNSAFE_STATUSES = {"overclaim", "implausible"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _receipt_id(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _has_specific_content(text: str) -> bool:
    """Check if the claim contains specific numbers, units, or citations.

    Specificity is NOT truth. A specific claim can still be wrong.
    """
    lower = text.lower()
    # Numbers with units
    if re.search(
        r'\d+\.?\d*\s*'
        r'(hz|mhz|ghz|thz|ev|mev|gev|tev|nm|mm|cm|m|kg|s|ms|'
        r'µs|percent|%|km|kw|mw|gw)',
        lower,
    ):
        return True
    # Scientific notation
    if re.search(r'\d+\.?\d*\s*[×x]\s*10', text):
        return True
    # Citation patterns
    if re.search(r'[A-Z][a-z]+ et al\.', text):
        return True
    if re.search(r'\(\d{4}\)', text):
        return True
    # DOI
    if "doi:" in lower or "10." in text:
        return True
    return False


def check_claim(
    claim_text: str,
    *,
    model_id: str = "",
    seed_id: str = "",
    task_id: str = "",
    stop_panic: bool = False,
) -> dict:
    """Check a single claim. Returns a receipt.

    The checker is NOT authority. A claim passing the checker does NOT
    make it true. Plausible is NOT true. Passing a check is NOT proof.
    """
    if stop_panic:
        receipt = {
            "schema": SCHEMA_VERSION,
            "claim_text": claim_text,
            "model_id": model_id,
            "seed_id": seed_id,
            "task_id": task_id,
            "status": "unchecked",
            "flags": ["stop_panic"],
            "confidence_band": "low",
            "reasons": ["STOP/PANIC — check blocked"],
            "operator_review_required": True,
            "blocked": True,
            **_INVARIANTS,
        }
        receipt["receipt_id"] = _receipt_id(receipt)
        return receipt

    flags = []
    reasons = []
    status = "unchecked"
    confidence_band = "low"

    # Check for overclaim (highest priority)
    overclaim_terms = detect_unsafe_overclaim(claim_text)
    if overclaim_terms:
        status = "overclaim"
        flags.append("unsafe_overclaim")
        reasons.append(
            f"Unsafe overclaim terms detected: {', '.join(overclaim_terms)}"
        )
        confidence_band = "high"

    # Check for fake falsification
    elif detect_fake_falsification(claim_text):
        status = "implausible"
        flags.append("fake_falsification")
        reasons.append(
            "Claims falsification without measurable criteria"
        )
        confidence_band = "medium"

    # Check for generic slop
    elif detect_generic_slop(claim_text):
        status = "needs_review"
        flags.append("generic_slop")
        reasons.append(
            "Content matches generic slop patterns — needs operator review"
        )
        confidence_band = "low"

    # Check for specific content (plausible but NOT true)
    elif _has_specific_content(claim_text):
        status = "plausible"
        reasons.append(
            "Claim contains specific content (numbers/units/citations). "
            "Plausible is NOT true — operator verification required."
        )
        confidence_band = "medium"

    else:
        status = "unchecked"
        reasons.append("No specific patterns detected — status unchecked")
        confidence_band = "low"

    operator_review_required = status in _REVIEW_STATUSES

    receipt = {
        "schema": SCHEMA_VERSION,
        "claim_text": claim_text,
        "model_id": model_id,
        "seed_id": seed_id,
        "task_id": task_id,
        "status": status,
        "flags": flags,
        "confidence_band": confidence_band,
        "reasons": reasons,
        "operator_review_required": operator_review_required,
        "blocked": False,
        "checked_at": _utc_now_iso(),
        **_INVARIANTS,
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return receipt


def check_claims_batch(
    claims: list,
    *,
    run_id: str = "",
    stop_panic: bool = False,
) -> dict:
    """Check multiple claims. Returns a batch receipt.

    Each claim: {"claim_text": str, "model_id": str, "seed_id": str,
    "task_id": str}

    The checker is NOT authority. Passing all checks is NOT proof.
    """
    results = []
    for claim in claims:
        r = check_claim(
            claim.get("claim_text", ""),
            model_id=claim.get("model_id", ""),
            seed_id=claim.get("seed_id", ""),
            task_id=claim.get("task_id", ""),
            stop_panic=stop_panic,
        )
        results.append(r)

    # Summary counts by status
    status_counts = {}
    for r in results:
        s = r.get("status", "unchecked")
        status_counts[s] = status_counts.get(s, 0) + 1

    any_unsafe = any(
        r.get("status") in _REVIEW_STATUSES for r in results
    )

    batch = {
        "schema": SCHEMA_VERSION,
        "receipt_type": "batch_claim_check",
        "run_id": run_id,
        "total": len(results),
        "results": results,
        "summary": status_counts,
        "operator_review_required": any_unsafe or stop_panic,
        "blocked": stop_panic,
        "checked_at": _utc_now_iso(),
        **_INVARIANTS,
    }
    batch["receipt_id"] = _receipt_id(batch)
    return batch


def is_safe_for_display(receipt: dict) -> bool:
    """True only if status not in unsafe set and no unsafe flags.

    Safe for display does NOT mean true. It means the claim did not
    trigger unsafe patterns.
    """
    status = receipt.get("status", "unchecked")
    if status in _UNSAFE_STATUSES:
        return False
    flags = receipt.get("flags", [])
    if "unsafe_overclaim" in flags:
        return False
    return True


def needs_operator_review(receipt: dict) -> bool:
    """True if status requires operator review.

    Operator review is a safety gate, not a truth mechanism.
    """
    status = receipt.get("status", "unchecked")
    return status in _REVIEW_STATUSES


def validate_claim_receipt(receipt: dict) -> list[str]:
    """Validate a claim receipt's invariants.
    Returns list of errors (empty = valid)."""
    errors = []

    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, "
            f"got {receipt.get('schema')}"
        )

    # Core invariants — must ALWAYS hold
    if receipt.get("checker_is_not_authority") is not True:
        errors.append("checker_is_not_authority must be True")

    if receipt.get("plausible_is_not_true") is not True:
        errors.append("plausible_is_not_true must be True")

    if receipt.get("passing_check_is_not_proof") is not True:
        errors.append("passing_check_is_not_proof must be True")

    if receipt.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    if receipt.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")

    # Status must be valid
    status = receipt.get("status")
    if status is not None and status not in CLAIM_STATUSES:
        errors.append(f"unknown status: {status}")

    # Operator review required for unsafe statuses
    if status in _REVIEW_STATUSES:
        if not receipt.get("operator_review_required"):
            errors.append(
                f"operator_review_required must be True for status '{status}'"
            )

    return errors
