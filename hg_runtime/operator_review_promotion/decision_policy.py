"""ORP-0 decision policy receipt."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash


def build_promotion_policy_receipt() -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "promotion_policy_receipt_v1",
        "policy_id": "orp0-operator-review-promotion-policy",
        "operator_review_is_truth": False,
        "operator_approval_is_action_permission": False,
        "operator_approval_authorizes_tools": False,
        "operator_approval_authorizes_web": False,
        "operator_approval_authorizes_providers": False,
        "operator_rejection_is_deletion": False,
        "operator_deferral_is_failure": False,
        "promotion_request_is_promotion": False,
        "promotion_gate_is_truth": False,
        "automatic_belief_promotion_allowed": False,
        "live_effects_allowed": False,
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy
