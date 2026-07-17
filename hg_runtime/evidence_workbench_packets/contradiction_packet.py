"""Contradiction packet records."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.evidence_workbench_packets.packet import FIXED_TIME


def build_packet_contradiction_record(
    *,
    contradiction_id: str,
    claim_id: str,
    participant_source_ids: list[str],
    conflict_class: str,
    stale_signal: bool = False,
    quarantine_signal: bool = False,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "packet_contradiction_record_v1",
        "contradiction_id": contradiction_id,
        "claim_id": claim_id,
        "participant_source_ids": participant_source_ids,
        "conflict_class": conflict_class,
        "stale_signal": stale_signal,
        "quarantine_signal": quarantine_signal,
        "conflict_status": "UNRESOLVED",
        "created_at": FIXED_TIME,
        "doctrine_note": "Contradiction record is not resolution.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_contradiction_review_packet(
    *,
    packet_id: str,
    claim_id: str,
    contradiction_record_ids: list[str],
    cluster_id: str | None = None,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "contradiction_review_packet_v1",
        "packet_id": packet_id,
        "claim_id": claim_id,
        "cluster_id": cluster_id,
        "contradiction_record_ids": contradiction_record_ids,
        "created_at": FIXED_TIME,
        "doctrine_note": "Contradiction review packet is not truth resolution.",
        **neutral_flags(),
    }
    record["packet_hash"] = record_hash(record)
    assert_neutral(record)
    return record
