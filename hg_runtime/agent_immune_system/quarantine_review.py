"""AIS-3 quarantine review tasks."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import assert_neutral, neutral_flags


def build_quarantine_review_task(
    *,
    review_task_id: str,
    quarantine_id: str,
    review_reason: str,
    review_path: str = "operator_review_required",
) -> dict:
    task = {
        "schema_version": "1",
        "record_type": "quarantine_review_task_v1",
        "review_task_id": review_task_id,
        "quarantine_id": quarantine_id,
        "review_reason": review_reason,
        "review_path": review_path,
        "operator_review_required": True,
        "quarantine_does_not_mark_guilty": True,
        "patch_authorized": False,
        "deletion_authorized": False,
        **neutral_flags(),
    }
    task["record_hash"] = record_hash(task)
    assert_neutral(task)
    return task
