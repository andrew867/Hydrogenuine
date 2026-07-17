"""EWP-3 contradiction review packet builder."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.claim_packet_builder import build_claim_evidence_packets, build_ewp1_inputs
from hg_runtime.evidence_workbench_packets.contradiction_packet import build_contradiction_review_packet
from hg_runtime.evidence_workbench_packets.conflict_cluster_packet import build_contradiction_cluster_packet


def build_contradiction_review_layer() -> dict:
    ewp1 = build_claim_evidence_packets(build_ewp1_inputs())
    contradiction_packets: list[dict] = []
    cluster_packets: list[dict] = []

    claims_with_contradictions: dict[str, list[str]] = {}
    for row in ewp1["packet_contradiction_records"]:
        claims_with_contradictions.setdefault(row["claim_id"], []).append(row["contradiction_id"])

    for idx, (claim_id, contradiction_ids) in enumerate(sorted(claims_with_contradictions.items()), start=1):
        packet = build_contradiction_review_packet(
            packet_id=f"ewp3-contradiction-packet-{idx:03d}",
            claim_id=claim_id,
            contradiction_record_ids=contradiction_ids,
            cluster_id=f"ewp3-cluster-{idx:03d}",
        )
        contradiction_packets.append(packet)
        cluster_packets.append(
            build_contradiction_cluster_packet(
                cluster_id=f"ewp3-cluster-{idx:03d}",
                claim_id=claim_id,
                contradiction_record_ids=contradiction_ids,
            )
        )

    return {
        "contradiction_review_packets": contradiction_packets,
        "contradiction_cluster_packets": cluster_packets,
        "source_contradiction_records": ewp1["packet_contradiction_records"],
    }
