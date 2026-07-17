"""DIB-2 parser quarantine registry."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.quarantine import build_parser_quarantine_record
from hg_runtime.document_intake_boundary.schemas import assert_neutral, record_hash


def build_quarantine_candidate(
    *,
    quarantine_id: str,
    file_id: str,
    parser_id: str,
    parser_status: str,
    reason: str,
) -> dict:
    record = build_parser_quarantine_record(quarantine_id=quarantine_id, file_id=file_id, reason=reason)
    record["parser_id"] = parser_id
    record["parser_status"] = parser_status
    record["quarantine_candidate"] = True
    record["auto_quarantine_enforced"] = False
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def register_quarantine_records(*, candidates: list[dict]) -> list[dict]:
    return list(candidates)
