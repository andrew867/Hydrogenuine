"""AIS quarantine_record_v1 — append-only, not deletion."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import AISImmuneError, assert_neutral, neutral_flags


def build_quarantine_record(
    *,
    quarantine_id: str,
    artifact_type: str,
    original_ref: str,
    content_hash: str,
    reason: str,
    review_task_id: str,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "quarantine_record_v1",
        "quarantine_id": quarantine_id,
        "artifact_type": artifact_type,
        "original_ref": original_ref,
        "content_hash": content_hash,
        "reason": reason,
        "review_task_id": review_task_id,
        "reversible": True,
        "quarantine_is_not_deletion": True,
        "deletion_performed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def validate_quarantine_record(record: dict) -> None:
    if not record.get("quarantine_is_not_deletion"):
        raise AISImmuneError("quarantine_is_not_deletion_required")
    if record.get("deletion_performed"):
        raise AISImmuneError("quarantine_deletion_forbidden")
    assert_neutral(record)
