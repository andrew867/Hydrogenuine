"""Conflict cluster packet records."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.evidence_workbench_packets.packet import FIXED_TIME


def build_contradiction_cluster_packet(
    *,
    cluster_id: str,
    claim_id: str,
    contradiction_record_ids: list[str],
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "contradiction_cluster_packet_v1",
        "cluster_id": cluster_id,
        "claim_id": claim_id,
        "contradiction_record_ids": contradiction_record_ids,
        "created_at": FIXED_TIME,
        "doctrine_note": "Conflict cluster is not proof.",
        "deletion_performed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
