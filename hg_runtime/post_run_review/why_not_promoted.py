"""Why-not-promoted explainer.

For any item, explains why it was not promoted to knowledge/memory.
This explainer does not make final judgments — it lists blocking reasons
and what an operator would need to consider.

Model output is not truth. Source is not truth. No promotion.
"""

from __future__ import annotations

BLOCKING_REASONS = {
    "source_is_not_truth": "Source text is treated as evidence candidate, not truth.",
    "model_output_is_not_truth": "Model output is treated as candidate, not truth.",
    "screenshot_is_not_proof": "Screenshot is observation evidence, not proof.",
    "no_operator_review": "No operator has reviewed this item.",
    "missing_gate_receipt": "No gate receipt confirms this item passed review.",
    "contradiction_unresolved": "A contradiction involving this item is unresolved.",
    "evidence_gap_present": "Evidence gaps exist for claims related to this item.",
    "unsupported_leap": "Item contains claims that go beyond source evidence.",
    "speculative_bridge": "Item bridges from evidence to speculation without marking it.",
    "weak_quality_score": "Quality adjudication flagged issues with this item.",
    "public_claim_flag": "Public claim checker flagged unsafe language.",
    "promotion_disabled_by_policy": "Promotion is disabled by manifest policy.",
    "candidate_knowledge_is_not_knowledge": "Candidate knowledge requires operator review.",
    "memory_promotion_requires_operator_review": "Memory promotion requires operator sign-off.",
    "memory_promotion_requires_gate_receipt": "Memory promotion requires a passing gate.",
}


def explain_why_not_promoted(
    *,
    item_id: str = "",
    item_type: str = "unknown",
    promotion_allowed: bool = False,
    operator_reviewed: bool = False,
    gate_receipt_present: bool = False,
    contradictions_unresolved: int = 0,
    evidence_gaps: int = 0,
    unsupported_leaps: int = 0,
    speculative_bridges: int = 0,
    quality_issues: int = 0,
    public_claim_flags: int = 0,
    is_source: bool = False,
    is_model_output: bool = False,
    is_screenshot: bool = False,
) -> dict:
    """Explain why an item was not promoted.

    Returns a dict with item_id, blocking_reasons, next_action, and
    what_cannot_be_concluded.
    """
    reasons = []

    if not promotion_allowed:
        reasons.append("promotion_disabled_by_policy")

    if is_source:
        reasons.append("source_is_not_truth")
    if is_model_output:
        reasons.append("model_output_is_not_truth")
    if is_screenshot:
        reasons.append("screenshot_is_not_proof")

    if not operator_reviewed:
        reasons.append("no_operator_review")
    if not gate_receipt_present:
        reasons.append("missing_gate_receipt")
    if contradictions_unresolved > 0:
        reasons.append("contradiction_unresolved")
    if evidence_gaps > 0:
        reasons.append("evidence_gap_present")
    if unsupported_leaps > 0:
        reasons.append("unsupported_leap")
    if speculative_bridges > 0:
        reasons.append("speculative_bridge")
    if quality_issues > 0:
        reasons.append("weak_quality_score")
    if public_claim_flags > 0:
        reasons.append("public_claim_flag")

    if item_type in ("memory_candidate", "knowledge_candidate"):
        reasons.append("candidate_knowledge_is_not_knowledge")
        reasons.append("memory_promotion_requires_operator_review")
        if not gate_receipt_present:
            reasons.append("memory_promotion_requires_gate_receipt")

    reason_details = [
        {"reason": r, "explanation": BLOCKING_REASONS.get(r, r)}
        for r in reasons
    ]

    next_action = "Operator review required."
    if contradictions_unresolved > 0:
        next_action = "Resolve contradictions, then operator review."
    elif evidence_gaps > 0:
        next_action = "Address evidence gaps, then operator review."

    return {
        "item_id": item_id,
        "item_type": item_type,
        "promotion_allowed": False,
        "operator_review_required": True,
        "blocking_reasons": reason_details,
        "blocking_reason_count": len(reasons),
        "next_possible_operator_action": next_action,
        "what_cannot_be_concluded": (
            "This item cannot be concluded as truth, knowledge, or "
            "established fact without operator review and gate receipt."
        ),
    }
