"""EWP-1 deterministic fixture inputs mimicking upstream LEB/ORP/SQP artifacts."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.fixtures import build_sqp1_duplicate_fixture_records
from hg_runtime.source_quality_provenance.provenance_graph_builder import build_sqp3_provenance_inputs
from hg_runtime.source_quality_provenance.review_policy_adapter import build_sqp5_inputs
from hg_runtime.source_quality_provenance.source_conflict_detector import (
    build_sqp4_inputs,
    build_staleness_conflict_layer,
)


def build_ewp1_inputs() -> dict:
    """Local fixtures only — no files read, no providers called."""
    provenance_inputs = build_sqp3_provenance_inputs()
    duplicate_records = build_sqp1_duplicate_fixture_records()
    sqp3_duplicate = {
        "record_type": "duplicate_source_record_v1",
        "primary_source_id": "sqp3-source-001",
        "duplicate_source_id": "sqp3-source-001-copy",
        "duplicate_class": "EXACT_CONTENT_DUPLICATE",
        "duplicate_treated_as_corroboration": False,
        "many_copies_treated_as_many_sources": False,
        "independent_corroboration_count": 1,
        "deletion_performed": False,
    }
    sqp4_layer = build_staleness_conflict_layer(build_sqp4_inputs())
    review_hints = build_sqp5_inputs()
    return {
        "claim_links": [
            {
                "claim_link_id": "ewp1-claim-link-001",
                "claim_id": "ewp1-claim-001",
                "claim_text": "Local evidence supports fixture claim A.",
                "receipt_id": "sqp3-receipt-001",
                "source_id": "sqp3-source-001",
            },
            {
                "claim_link_id": "ewp1-claim-link-001b",
                "claim_id": "ewp1-claim-001",
                "claim_text": "Duplicate copy of fixture claim A evidence.",
                "receipt_id": "sqp3-receipt-001",
                "source_id": "sqp3-source-001-copy",
            },
            {
                "claim_link_id": "ewp1-claim-link-002",
                "claim_id": "ewp1-claim-002",
                "claim_text": "Conflicting local evidence for fixture claim B.",
                "receipt_id": "sqp3-receipt-002",
                "source_id": "sqp3-source-002",
            },
            {
                "claim_link_id": "ewp1-claim-link-003",
                "claim_id": "ewp1-claim-003",
                "claim_text": "Single-source claim requiring second source.",
                "receipt_id": "sqp3-receipt-001",
                "source_id": "sqp3-source-001",
            },
        ],
        "reviewed_links": provenance_inputs["reviewed_links"],
        "belief_revisions": provenance_inputs["belief_states"],
        "fingerprints": provenance_inputs["fingerprints"],
        "duplicate_records": duplicate_records["duplicate_source_records"] + [sqp3_duplicate],
        "quality_scores": provenance_inputs["quality_scores"],
        "provenance_graph_ref": "docs/proofs/autonomous_agent_zero/SQP-3-PROVENANCE-GRAPH",
        "staleness_records": sqp4_layer["staleness_records"],
        "conflict_records": sqp4_layer["conflict_records"],
        "review_hints": review_hints["sources"],
    }


def build_claim_evidence_packets(inputs: dict) -> dict:
    from hg_runtime.evidence_workbench_packets.contradiction_packet import build_packet_contradiction_record
    from hg_runtime.evidence_workbench_packets.packet_source_summary_builder import build_source_summaries
    from hg_runtime.evidence_workbench_packets.packet_support_builder import build_support_records

    claim_packets = []
    all_summaries = []
    all_supports = []
    all_contradictions = []

    quality_by_source = {row["source_id"]: row["quality_band"] for row in inputs["quality_scores"]}
    conflict_by_source: dict[str, list[str]] = {}
    for conflict in inputs["conflict_records"]:
        for sid in conflict["participant_source_ids"]:
            conflict_by_source.setdefault(sid, []).append(conflict["conflict_class"])

    duplicate_primary: dict[str, str] = {}
    duplicate_members: dict[str, list[str]] = {}
    for dup in inputs["duplicate_records"]:
        if dup.get("duplicate_class") in {"EXACT_CONTENT_DUPLICATE", "NORMALIZED_TEXT_DUPLICATE", "SAME_TEXT_DIFFERENT_PATH"}:
            primary = dup["primary_source_id"]
            duplicate = dup["duplicate_source_id"]
            duplicate_primary[duplicate] = primary
            duplicate_members.setdefault(primary, [primary]).append(duplicate)

    claims: dict[str, dict] = {}
    for link in inputs["claim_links"]:
        entry = claims.setdefault(
            link["claim_id"],
            {"claim_id": link["claim_id"], "claim_text": link["claim_text"], "source_ids": [], "receipt_id": link["receipt_id"]},
        )
        entry["source_ids"].append(link["source_id"])

    for idx, (claim_id, claim) in enumerate(sorted(claims.items()), start=1):
        source_ids = claim["source_ids"]
        collapsed_ids: list[str] = []
        seen: set[str] = set()
        for source_id in source_ids:
            primary_source = duplicate_primary.get(source_id, source_id)
            for sid in duplicate_members.get(primary_source, [primary_source]):
                if sid not in seen:
                    seen.add(sid)
                    collapsed_ids.append(sid)
        primary_source = duplicate_primary.get(source_ids[0], source_ids[0])

        summaries = build_source_summaries(
            claim_id=claim_id,
            source_ids=collapsed_ids,
            quality_by_source=quality_by_source,
            provenance_graph_ref=inputs["provenance_graph_ref"],
            duplicate_collapsed=len(collapsed_ids) > 1,
        )
        supports = build_support_records(
            claim_id=claim_id,
            source_id=primary_source,
            receipt_ref=f"leb:receipt:{claim['receipt_id']}",
            reviewed_links=inputs["reviewed_links"],
        )
        summary_ids = [row["summary_id"] for row in summaries]
        support_ids = [row["support_id"] for row in supports]

        contradiction_ids: list[str] = []
        for sid in collapsed_ids:
            if sid in conflict_by_source:
                contradiction = build_packet_contradiction_record(
                    contradiction_id=f"ewp1-contradiction-{claim_id}-{sid}",
                    claim_id=claim_id,
                    participant_source_ids=[sid],
                    conflict_class=conflict_by_source[sid][0],
                )
                contradiction_ids.append(contradiction["contradiction_id"])
                all_contradictions.append(contradiction)

        if claim_id == "ewp1-claim-002" and not contradiction_ids:
            contradiction = build_packet_contradiction_record(
                contradiction_id=f"ewp1-contradiction-{claim_id}-fixture",
                claim_id=claim_id,
                participant_source_ids=collapsed_ids + ["sqp3-source-002"],
                conflict_class="CLAIM_CONFLICT",
            )
            contradiction_ids.append(contradiction["contradiction_id"])
            all_contradictions.append(contradiction)

        if claim_id == "ewp1-claim-003" and not contradiction_ids:
            contradiction = build_packet_contradiction_record(
                contradiction_id=f"ewp1-contradiction-{claim_id}-stale",
                claim_id=claim_id,
                participant_source_ids=collapsed_ids,
                conflict_class="RETRACTION_CONFLICT",
                stale_signal=True,
                quarantine_signal=True,
            )
            contradiction_ids.append(contradiction["contradiction_id"])
            all_contradictions.append(contradiction)

        from hg_runtime.evidence_workbench_packets.claim_packet import build_claim_evidence_packet

        packet = build_claim_evidence_packet(
            packet_id=f"ewp1-claim-packet-{idx:03d}",
            claim_id=claim_id,
            claim_text=claim["claim_text"],
            source_summary_ids=summary_ids,
            support_record_ids=support_ids,
            contradiction_record_ids=contradiction_ids,
        )
        claim_packets.append(packet)
        all_summaries.extend(summaries)
        all_supports.extend(supports)

    return {
        "claim_evidence_packets": claim_packets,
        "packet_source_summaries": all_summaries,
        "packet_support_records": all_supports,
        "packet_contradiction_records": all_contradictions,
    }
