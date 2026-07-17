"""AIS immune_memory_record_v1 — append-only."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import assert_neutral, neutral_flags


def build_immune_memory_record(
    *,
    memory_id: str,
    memory_type: str,
    summary: str,
    signature_id: str | None = None,
    closure_receipt_ref: str | None = None,
    phase_ref: str | None = None,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "immune_memory_record_v1",
        "memory_id": memory_id,
        "memory_type": memory_type,
        "summary": summary,
        "signature_id": signature_id,
        "closure_receipt_ref": closure_receipt_ref,
        "phase_ref": phase_ref,
        "immune_memory_is_append_only": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
