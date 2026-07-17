"""World-model record audit entries."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    AUDIT_STATUSES,
    RECORD_AUDIT_SCHEMA,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_record_audit(
    *,
    record_kind: str,
    record_id: str,
    source_phase: str,
    audit_status: str = "OPEN",
    visibility_preserved: bool = True,
    notes: str = "",
) -> dict:
    if audit_status not in AUDIT_STATUSES:
        raise ValueError(f"invalid_audit_status:{audit_status}")
    record = {
        "schema": RECORD_AUDIT_SCHEMA,
        "audit_id": f"audit-{record_kind}-{record_id}",
        "record_kind": record_kind,
        "record_id": record_id,
        "source_phase": source_phase,
        "audit_status": audit_status,
        "visibility_preserved": visibility_preserved,
        "deletion_performed": False,
        "rewrite_performed": False,
        "audit_notes": notes,
        **neutral_flags(),
    }
    record["audit_hash"] = canonical_hash(record)
    assert_neutral(record)
    return record


def validate_record_audit(record: dict) -> None:
    if record.get("schema") != RECORD_AUDIT_SCHEMA:
        raise ValueError("invalid_record_audit_schema")
    if record.get("deletion_performed"):
        raise ValueError("deletion_performed_forbidden")
    if record.get("rewrite_performed"):
        raise ValueError("rewrite_performed_forbidden")
    assert_neutral(record)
