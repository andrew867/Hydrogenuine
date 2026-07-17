"""Packet source summary records."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.evidence_workbench_packets.packet import FIXED_TIME


def build_packet_source_summary(
    *,
    summary_id: str,
    source_id: str,
    quality_band: str,
    provenance_path_ref: str,
    duplicate_collapsed: bool = False,
    original_source_ids: list[str] | None = None,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "packet_source_summary_v1",
        "summary_id": summary_id,
        "source_id": source_id,
        "quality_band": quality_band,
        "provenance_path_ref": provenance_path_ref,
        "duplicate_collapsed": duplicate_collapsed,
        "original_source_ids": original_source_ids or [source_id],
        "created_at": FIXED_TIME,
        "doctrine_note": "Source quality summary is not authority.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_packet_support_record(
    *,
    support_id: str,
    claim_id: str,
    source_id: str,
    receipt_ref: str,
    review_decision_ref: str | None = None,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "packet_support_record_v1",
        "support_id": support_id,
        "claim_id": claim_id,
        "source_id": source_id,
        "receipt_ref": receipt_ref,
        "review_decision_ref": review_decision_ref,
        "created_at": FIXED_TIME,
        "doctrine_note": "Support record is not proof.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
