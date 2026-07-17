"""LEB-5 evidence review task.

A review task records that a local evidence receipt or LEB output should be seen
by an operator. It is metadata only: not an action, not a belief promotion, not a
tool authorization, and not an operator approval.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

VALID_RECOMMENDED_ACTIONS = ("OPERATOR_REVIEW", "QUARANTINE_CANDIDATE")


def _target_id(record: dict) -> str:
    for key in ("receipt_id", "link_id", "belief_state_id", "revision_id", "contradiction_id", "record_id"):
        if key in record:
            return record[key]
    return record.get("record_type", "unknown")


def _target_hash(record: dict) -> str:
    return record.get("record_hash") or record.get("receipt_hash") or ""


def build_review_task(*, task_id: str, target: dict, recommended_action: str, reason: str, fever_level: str, restricted: bool) -> dict:
    if recommended_action not in VALID_RECOMMENDED_ACTIONS:
        raise EvidenceBridgeError(f"invalid_recommended_action:{recommended_action}")
    status = "RESTRICTED_PENDING_OPERATOR_REVIEW" if restricted else "PENDING_OPERATOR_REVIEW"
    task = {
        "schema_version": "1",
        "record_type": "evidence_review_task_v1",
        "review_task_id": task_id,
        "target_record_id": _target_id(target),
        "target_record_kind": target.get("record_type", "unknown"),
        "target_record_hash": _target_hash(target),
        "review_status": status,
        "recommended_action": recommended_action,
        "reason": reason,
        "fever_level": fever_level,
        "quarantine_candidate": recommended_action == "QUARANTINE_CANDIDATE",
        "review_task_is_action": False,
        "review_task_is_belief_promotion": False,
        "review_task_is_operator_approval": False,
        "review_task_is_tool_authorization": False,
        "automatic_patching": False,
        "deletion_performed": False,
        **neutral_flags(),
    }
    task["record_hash"] = record_hash(task)
    assert_neutral(task)
    return task
