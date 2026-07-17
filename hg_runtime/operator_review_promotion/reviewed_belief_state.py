"""Reviewed local belief state records for ORP-4.

Reviewed means an operator decision and promotion gate are present. It does not
mean true, certain, authoritative, or actionable.
"""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash


def build_reviewed_local_belief_state(*, state_id: str, revision_input: dict, status: str = "PROVISIONALLY_SUPPORTED") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "reviewed_local_belief_state_v1",
        "reviewed_belief_state_id": state_id,
        "revision_input_id": revision_input["revision_input_id"],
        "revision_input_hash": revision_input["record_hash"],
        "target_record_id": revision_input["target_record_id"],
        "target_record_hash": revision_input["target_record_hash"],
        "belief_status": status,
        "operator_reviewed": True,
        "operator_reviewed_means_true": False,
        "reviewed_belief_is_still_provisional": True,
        "belief_state_is_truth": False,
        "truth_claimed": False,
        "certainty_claimed": False,
        "support_level": "PROVISIONALLY_SUPPORTED" if status == "PROVISIONALLY_SUPPORTED" else status,
        "old_records_preserved": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_reviewed_local_belief_revision(*, revision_id: str, state: dict, from_status: str = "UNVERIFIED") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "reviewed_local_belief_revision_v1",
        "reviewed_revision_id": revision_id,
        "reviewed_belief_state_id": state["reviewed_belief_state_id"],
        "target_record_id": state["target_record_id"],
        "from_status": from_status,
        "to_status": state["belief_status"],
        "revision_reason": "PROMOTION_GATED_OPERATOR_REVIEW_LOCAL_EVIDENCE",
        "belief_revision_is_certainty": False,
        "truth_claimed": False,
        "certainty_claimed": False,
        "old_records_preserved": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_reviewed_local_contradiction(*, contradiction_id: str, rejected_record_id: str, preserved_hash: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "reviewed_local_contradiction_v1",
        "contradiction_id": contradiction_id,
        "source_record_id": rejected_record_id,
        "source_record_hash": preserved_hash,
        "contradiction_status": "UNRESOLVED_REJECTED_EVIDENCE_PRESERVED",
        "truth_resolved": False,
        "operator_reviewed_means_true": False,
        "rejected_evidence_excluded_but_preserved": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_reviewed_local_provenance_chain(*, provenance_id: str, state: dict, revision_input: dict) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "reviewed_local_provenance_chain_v1",
        "provenance_chain_id": provenance_id,
        "reviewed_belief_state_id": state["reviewed_belief_state_id"],
        "revision_input_id": revision_input["revision_input_id"],
        "promotion_gate_result_id": revision_input["promotion_gate_result_id"],
        "promotion_request_id": revision_input["promotion_request_id"],
        "target_record_id": revision_input["target_record_id"],
        "target_record_hash": revision_input["target_record_hash"],
        "provenance_chain_is_not_truth": True,
        "old_records_preserved": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
