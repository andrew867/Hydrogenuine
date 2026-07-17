"""Evidence workbench packet records."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import assert_neutral, neutral_flags, record_hash

FIXED_TIME = "2026-06-20T00:00:00Z"


def build_evidence_workbench_packet(*, packet_id: str, claim_id: str, packet_kind: str = "CLAIM_EVIDENCE") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "evidence_workbench_packet_v1",
        "packet_id": packet_id,
        "claim_id": claim_id,
        "packet_kind": packet_kind,
        "created_at": FIXED_TIME,
        "doctrine_note": "Evidence packet is not truth.",
        **neutral_flags(),
    }
    record["packet_hash"] = record_hash(record)
    assert_neutral(record)
    return record
