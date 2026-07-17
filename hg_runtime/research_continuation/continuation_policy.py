"""Continuation policy — decide which seeds/tasks get continued."""

from __future__ import annotations

SCHEMA_VERSION = "continuation_policy_v1"

CONTINUATION_DECISIONS = {
    "CONTINUE",
    "CONTINUE_WITH_DIFFERENT_MODEL",
    "CONTINUE_WITH_OPERATOR_REVIEW",
    "DROP_LOW_VALUE",
    "DROP_UNSAFE",
    "HOLD_PENDING_SOURCE",
    "HOLD_PENDING_EVIDENCE",
}


def evaluate_continuation(*, seed_id: str, quality_class: str,
                          issue_categories: list[str], model_id: str,
                          cycle_count: int, evidence_gap_count: int,
                          operator_review_pending: bool = False) -> dict:
    """Decide whether a seed/task should continue."""
    decision = "CONTINUE"
    reasons = []

    if quality_class == "REJECT_UNSAFE_OVERCLAIM":
        decision = "DROP_UNSAFE"
        reasons.append("unsafe_overclaim_rejected")
    elif quality_class == "REJECT_UNSUPPORTED":
        decision = "DROP_LOW_VALUE"
        reasons.append("unsupported_claims_rejected")
    elif quality_class == "RETRY_WITH_DIFFERENT_MODEL":
        decision = "CONTINUE_WITH_DIFFERENT_MODEL"
        reasons.append("prior_model_produced_weak_output")
    elif quality_class == "LOW_VALUE_TRIAGE":
        if cycle_count >= 3:
            decision = "DROP_LOW_VALUE"
            reasons.append("low_value_after_multiple_cycles")
        else:
            decision = "CONTINUE_WITH_DIFFERENT_MODEL"
            reasons.append("low_value_retryable")
    elif quality_class in {"HIGH_VALUE", "USABLE_WITH_CAVEATS"}:
        if evidence_gap_count > 0:
            decision = "HOLD_PENDING_EVIDENCE"
            reasons.append("evidence_gaps_outstanding")
        elif operator_review_pending:
            decision = "CONTINUE_WITH_OPERATOR_REVIEW"
            reasons.append("operator_review_pending")
        else:
            decision = "CONTINUE"
    else:
        decision = "CONTINUE"

    if "unsafe_overclaim" in issue_categories:
        decision = "DROP_UNSAFE"
        reasons.append("unsafe_overclaim_in_issues")

    return {
        "seed_id": seed_id,
        "decision": decision,
        "reasons": reasons,
        "model_id": model_id,
        "cycle_count": cycle_count,
        "quality_class": quality_class,
        "continuation_grants_authority": False,
        "continuation_promotes_to_truth": False,
    }
