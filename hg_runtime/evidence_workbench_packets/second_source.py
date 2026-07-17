"""Second-source requirement and result records."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import (
    SECOND_SOURCE_OUTCOMES,
    assert_neutral,
    neutral_flags,
    record_hash,
)
from hg_runtime.evidence_workbench_packets.packet import FIXED_TIME


def build_packet_second_source_requirement(
    *,
    requirement_id: str,
    packet_id: str,
    claim_id: str,
    second_source_required: bool,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "packet_second_source_requirement_v1",
        "requirement_id": requirement_id,
        "packet_id": packet_id,
        "claim_id": claim_id,
        "second_source_required": second_source_required,
        "created_at": FIXED_TIME,
        "doctrine_note": "Second source requirement is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_packet_second_source_result(
    *,
    result_id: str,
    requirement_id: str,
    packet_id: str,
    outcome: str,
    independent_source_count: int = 0,
) -> dict:
    if outcome not in SECOND_SOURCE_OUTCOMES:
        raise ValueError(f"invalid_second_source_outcome:{outcome}")
    record = {
        "schema_version": "1",
        "record_type": "packet_second_source_result_v1",
        "result_id": result_id,
        "requirement_id": requirement_id,
        "packet_id": packet_id,
        "outcome": outcome,
        "independent_source_count": independent_source_count,
        "created_at": FIXED_TIME,
        "doctrine_note": "Second source result is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
