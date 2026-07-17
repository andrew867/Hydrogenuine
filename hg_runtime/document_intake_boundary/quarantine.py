"""DIB quarantine record builder (schema foundation)."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_parser_quarantine_record(*, quarantine_id: str, file_id: str, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "parser_quarantine_record_v1",
        "quarantine_id": quarantine_id,
        "file_id": file_id,
        "reason": reason,
        "quarantine_is_deletion": False,
        "auto_quarantine_enforced": False,
        "deletion_performed": False,
        "original_preserved": True,
        "doctrine_note": "Quarantine is not deletion.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
