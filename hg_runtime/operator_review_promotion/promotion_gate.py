"""Promotion gate result records."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash


def build_promotion_gate_result(*, gate_result_id: str, request: dict, passed: bool = False, fail_reason: str = "NONE") -> dict:
    result = {
        "schema_version": "1",
        "record_type": "promotion_gate_result_v1",
        "promotion_gate_result_id": gate_result_id,
        "promotion_request_id": request["promotion_request_id"],
        "promotion_request_hash": request["request_hash"],
        "gate_passed": passed,
        "gate_fail_reason": fail_reason if not passed else "NONE",
        "promotion_gate_is_truth": False,
        "gate_pass_is_truth": False,
        "gate_pass_is_certainty": False,
        "gate_pass_is_action_permission": False,
        "gate_pass_authorizes_tools": False,
        "gate_pass_authorizes_web": False,
        "gate_pass_authorizes_providers": False,
        "gate_fail_is_deletion": False,
        "revision_input_created": passed,
        "revision_input_is_belief_state": False,
        "old_proof_mutated": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        **neutral_flags(),
    }
    result["gate_hash"] = record_hash(result)
    assert_neutral(result)
    return result
