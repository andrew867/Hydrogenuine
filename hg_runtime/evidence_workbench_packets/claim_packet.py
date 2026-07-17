"""Claim evidence packet records."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.evidence_workbench_packets.packet import FIXED_TIME


def build_claim_evidence_packet(
    *,
    packet_id: str,
    claim_id: str,
    claim_text: str,
    source_summary_ids: list[str],
    support_record_ids: list[str],
    contradiction_record_ids: list[str] | None = None,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "claim_evidence_packet_v1",
        "packet_id": packet_id,
        "claim_id": claim_id,
        "claim_text": claim_text,
        "source_summary_ids": source_summary_ids,
        "support_record_ids": support_record_ids,
        "contradiction_record_ids": contradiction_record_ids or [],
        "created_at": FIXED_TIME,
        "doctrine_note": "Claim packet is not truth or approval.",
        **neutral_flags(),
    }
    record["packet_hash"] = record_hash(record)
    assert_neutral(record)
    return record
