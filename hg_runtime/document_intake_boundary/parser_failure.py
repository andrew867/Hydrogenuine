"""DIB-2 parser failure record builders."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_parser_failure_record(
    *,
    failure_id: str,
    file_id: str,
    parser_id: str,
    parser_status: str,
    reason: str,
    quarantine_recommended: bool = False,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "parser_failure_record_v1",
        "failure_id": failure_id,
        "file_id": file_id,
        "parser_id": parser_id,
        "parser_status": parser_status,
        "reason": reason,
        "parser_success": False,
        "parser_success_treated_as_correctness": False,
        "parser_failure_is_deletion_permission": False,
        "deletion_performed": False,
        "original_preserved": True,
        "quarantine_recommended": quarantine_recommended,
        "doctrine_note": "Parser failure is not deletion permission.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
