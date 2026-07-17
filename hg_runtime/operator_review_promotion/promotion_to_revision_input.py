"""Promotion-gated local belief revision input records.

These records are bounded inputs for a later local revision pass. They are not
belief states, truth claims, action permission, or tool authorization.
"""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash


def build_promotion_gated_revision_input(*, input_id: str, gate_result: dict, request: dict) -> dict:
    if not gate_result["gate_passed"]:
        raise ValueError("cannot_create_revision_input_from_failed_gate")
    record = {
        "schema_version": "1",
        "record_type": "promotion_gated_revision_input_v1",
        "revision_input_id": input_id,
        "promotion_gate_result_id": gate_result["promotion_gate_result_id"],
        "promotion_gate_hash": gate_result["gate_hash"],
        "promotion_request_id": request["promotion_request_id"],
        "promotion_request_hash": request["request_hash"],
        "target_record_id": request["target_record_id"],
        "target_record_hash": request["target_record_hash"],
        "revision_input_use": "PROVISIONAL_LOCAL_BELIEF_REVISION_INPUT",
        "revision_input_is_belief_state": False,
        "gate_pass_is_truth": False,
        "gate_pass_is_certainty": False,
        "gate_pass_is_action_permission": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "old_proof_mutated": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
