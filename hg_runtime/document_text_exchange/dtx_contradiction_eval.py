"""DTX contradiction evaluation helpers."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.contradiction_packet import build_contradiction_review_packet, build_packet_contradiction_record


def build_contradiction_artifacts(*, spec: dict, claim_id: str) -> tuple[list[str], dict | None]:
    if spec["family_id"] not in {"CONTRADICTORY_TEXT", "STALE_TEXT"}:
        return [], None
    doc_ids = [doc["doc_id"] for doc in spec["documents"]]
    contradiction = build_packet_contradiction_record(
        contradiction_id=f"dtx-contradiction-{claim_id}",
        claim_id=claim_id,
        participant_source_ids=doc_ids,
        conflict_class="SOURCE_METADATA_CONFLICT" if spec["family_id"] == "STALE_TEXT" else "CLAIM_CONFLICT",
        stale_signal=spec["family_id"] == "STALE_TEXT",
    )
    packet = build_contradiction_review_packet(
        packet_id=f"dtx-contradiction-packet-{claim_id}",
        claim_id=claim_id,
        contradiction_record_ids=[contradiction["contradiction_id"]],
    )
    return [contradiction["contradiction_id"]], packet
