"""Source promotion guard — prevents source text from becoming knowledge.

Source is not truth. No promotion without operator review and gate passage.
No automatic knowledge creation from retrieved text, search snippets,
screenshots, or model summaries.
"""

from __future__ import annotations

PROMOTION_DECISIONS = {
    "reject",
    "defer",
    "candidate_only",
    "operator_review_required",
    "reject_pending_gate",
}

NEVER_PROMOTE_REASONS = {
    "source_text_is_not_truth",
    "search_snippet_is_not_evidence",
    "screenshot_is_observation_only",
    "model_summary_is_not_truth",
    "no_operator_review",
    "no_gate_passage",
    "unsafe_overclaim_detected",
}


def evaluate_promotion(*, source_receipt: dict | None = None,
                       boundary_audit: dict | None = None,
                       operator_approved: bool = False,
                       gate_passed: bool = False) -> dict:
    reasons = []

    if source_receipt and source_receipt.get("source_treated_as_truth"):
        reasons.append("source_treated_as_truth_flag_set")

    if boundary_audit:
        if boundary_audit.get("unsafe_overclaim_count", 0) > 0:
            reasons.append("unsafe_overclaim_detected")
        if not boundary_audit.get("all_claims_bounded", False):
            reasons.append("claims_not_bounded")

    if not operator_approved:
        reasons.append("no_operator_review")

    if not gate_passed:
        reasons.append("no_gate_passage")

    decision = "reject" if reasons else "candidate_only"

    return {
        "promotion_allowed": len(reasons) == 0 and operator_approved and gate_passed,
        "decision": decision,
        "rejection_reasons": reasons,
        "operator_approved": operator_approved,
        "gate_passed": gate_passed,
        "source_treated_as_truth": False,
        "model_output_treated_as_truth": False,
    }


def validate_promotion_decision(decision: dict) -> list[str]:
    errors = []
    if decision.get("decision") not in PROMOTION_DECISIONS:
        errors.append(f"unknown decision: {decision.get('decision')}")
    if decision.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if decision.get("model_output_treated_as_truth"):
        errors.append("model_output_treated_as_truth must be False")
    if decision.get("promotion_allowed") and not decision.get("operator_approved"):
        errors.append("promotion without operator approval")
    if decision.get("promotion_allowed") and not decision.get("gate_passed"):
        errors.append("promotion without gate passage")
    return errors
