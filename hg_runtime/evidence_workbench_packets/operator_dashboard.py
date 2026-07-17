"""Operator packet dashboard records."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import (
    PACKET_REVIEW_STATUSES,
    assert_neutral,
    neutral_flags,
    record_hash,
)
from hg_runtime.evidence_workbench_packets.packet import FIXED_TIME


def build_packet_review_status(
    *,
    status_id: str,
    packet_id: str,
    claim_id: str,
    review_status: str,
) -> dict:
    if review_status not in PACKET_REVIEW_STATUSES:
        raise ValueError(f"invalid_review_status:{review_status}")
    record = {
        "schema_version": "1",
        "record_type": "packet_review_status_v1",
        "status_id": status_id,
        "packet_id": packet_id,
        "claim_id": claim_id,
        "review_status": review_status,
        "created_at": FIXED_TIME,
        "doctrine_note": "Review status is not operator approval.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_operator_packet_dashboard(
    *,
    dashboard_id: str,
    claim_packet_count: int,
    second_source_result_count: int,
    contradiction_packet_count: int,
    review_status_summary: dict[str, int],
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "operator_packet_dashboard_v1",
        "dashboard_id": dashboard_id,
        "claim_packet_count": claim_packet_count,
        "second_source_result_count": second_source_result_count,
        "contradiction_packet_count": contradiction_packet_count,
        "review_status_summary": review_status_summary,
        "created_at": FIXED_TIME,
        "doctrine_note": "Dashboard is not operator approval.",
        **neutral_flags(),
    }
    record["dashboard_hash"] = record_hash(record)
    assert_neutral(record)
    return record
