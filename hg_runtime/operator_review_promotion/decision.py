"""Operator review decision records.

An operator review decision is a receipt over evidence review metadata. It is
not truth, not action permission, and not a tool authorization.
"""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import (
    DECISION_STATUSES,
    OperatorReviewPromotionError,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_operator_review_decision(
    *,
    decision_id: str,
    review_task: dict,
    status: str,
    reviewer_id: str = "operator-fixture",
    rationale: str = "fixture_review",
) -> dict:
    if status not in DECISION_STATUSES:
        raise OperatorReviewPromotionError(f"invalid_decision_status:{status}")
    decision = {
        "schema_version": "1",
        "record_type": "operator_review_decision_v1",
        "decision_id": decision_id,
        "review_task_id": review_task["review_task_id"],
        "target_record_id": review_task["target_record_id"],
        "target_record_kind": review_task["target_record_kind"],
        "target_record_hash": review_task["target_record_hash"],
        "decision_status": status,
        "reviewer_id": reviewer_id,
        "rationale": rationale,
        "append_only": True,
        "operator_review_is_truth": False,
        "operator_approval_is_action_permission": False,
        "operator_approval_authorizes_tools": False,
        "operator_approval_authorizes_web": False,
        "operator_approval_authorizes_providers": False,
        "operator_rejection_is_deletion": False,
        "operator_deferral_is_failure": False,
        "promotion_request_created": False,
        **neutral_flags(),
    }
    decision["decision_hash"] = record_hash(decision)
    assert_neutral(decision)
    return decision


def build_reviewed_evidence_link(*, link_id: str, decision: dict) -> dict:
    link = {
        "schema_version": "1",
        "record_type": "reviewed_evidence_link_v1",
        "link_id": link_id,
        "decision_id": decision["decision_id"],
        "decision_hash": decision["decision_hash"],
        "target_record_id": decision["target_record_id"],
        "target_record_hash": decision["target_record_hash"],
        "reviewed_status": decision["decision_status"],
        "reviewed_link_is_truth": False,
        "reviewed_link_authorizes_action": False,
        **neutral_flags(),
    }
    link["record_hash"] = record_hash(link)
    assert_neutral(link)
    return link


def build_operator_rejection_record(*, rejection_id: str, decision: dict) -> dict:
    if decision["decision_status"] != "REJECT_SOURCE":
        raise OperatorReviewPromotionError("rejection_requires_reject_source_decision")
    record = {
        "schema_version": "1",
        "record_type": "operator_rejection_record_v1",
        "rejection_id": rejection_id,
        "decision_id": decision["decision_id"],
        "decision_hash": decision["decision_hash"],
        "target_record_id": decision["target_record_id"],
        "original_evidence_preserved": True,
        "operator_rejection_is_deletion": False,
        "deletion_performed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_operator_deferral_record(*, deferral_id: str, decision: dict) -> dict:
    if decision["decision_status"] != "DEFER_REVIEW":
        raise OperatorReviewPromotionError("deferral_requires_defer_review_decision")
    record = {
        "schema_version": "1",
        "record_type": "operator_deferral_record_v1",
        "deferral_id": deferral_id,
        "decision_id": decision["decision_id"],
        "decision_hash": decision["decision_hash"],
        "target_record_id": decision["target_record_id"],
        "review_remains_open": True,
        "operator_deferral_is_failure": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
