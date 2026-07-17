"""Deterministic EWP schema foundation fixtures."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.claim_packet import build_claim_evidence_packet
from hg_runtime.evidence_workbench_packets.contradiction_packet import (
    build_contradiction_review_packet,
    build_packet_contradiction_record,
)
from hg_runtime.evidence_workbench_packets.operator_dashboard import (
    build_operator_packet_dashboard,
    build_packet_review_status,
)
from hg_runtime.evidence_workbench_packets.packet import build_evidence_workbench_packet
from hg_runtime.evidence_workbench_packets.second_source import (
    build_packet_second_source_requirement,
    build_packet_second_source_result,
)
from hg_runtime.evidence_workbench_packets.source_summary import (
    build_packet_source_summary,
    build_packet_support_record,
)


def build_ewp0_fixture_records() -> dict:
    workbench = build_evidence_workbench_packet(packet_id="ewp0-packet-001", claim_id="ewp0-claim-001")
    claim = build_claim_evidence_packet(
        packet_id="ewp0-claim-packet-001",
        claim_id="ewp0-claim-001",
        claim_text="Fixture claim for schema foundation.",
        source_summary_ids=["ewp0-summary-001", "ewp0-summary-002"],
        support_record_ids=["ewp0-support-001"],
        contradiction_record_ids=["ewp0-contradiction-001"],
    )
    summaries = [
        build_packet_source_summary(
            summary_id="ewp0-summary-001",
            source_id="ewp0-source-001",
            quality_band="REVIEWED_USABLE",
            provenance_path_ref="docs/proofs/autonomous_agent_zero/SQP-3-PROVENANCE-GRAPH",
        ),
        build_packet_source_summary(
            summary_id="ewp0-summary-002",
            source_id="ewp0-source-001-copy",
            quality_band="STRUCTURALLY_USABLE",
            provenance_path_ref="docs/proofs/autonomous_agent_zero/SQP-3-PROVENANCE-GRAPH",
            duplicate_collapsed=True,
            original_source_ids=["ewp0-source-001", "ewp0-source-001-copy"],
        ),
    ]
    supports = [
        build_packet_support_record(
            support_id="ewp0-support-001",
            claim_id="ewp0-claim-001",
            source_id="ewp0-source-001",
            receipt_ref="docs/proofs/autonomous_agent_zero/LEB-2-EVIDENCE-WMBR-LINKER",
            review_decision_ref="docs/proofs/autonomous_agent_zero/ORP-1-OPERATOR-REVIEW-DECISION-LEDGER",
        )
    ]
    contradictions = [
        build_packet_contradiction_record(
            contradiction_id="ewp0-contradiction-001",
            claim_id="ewp0-claim-001",
            participant_source_ids=["ewp0-source-001", "ewp0-source-002"],
            conflict_class="CLAIM_CONFLICT",
        )
    ]
    requirements = [
        build_packet_second_source_requirement(
            requirement_id="ewp0-req-001",
            packet_id="ewp0-claim-packet-001",
            claim_id="ewp0-claim-001",
            second_source_required=True,
        )
    ]
    second_source_results = [
        build_packet_second_source_result(
            result_id="ewp0-ssr-001",
            requirement_id="ewp0-req-001",
            packet_id="ewp0-claim-packet-001",
            outcome="SECOND_SOURCE_PRESENT_REVIEW_READY",
            independent_source_count=2,
        )
    ]
    contradictions.append(
        build_packet_contradiction_record(
            contradiction_id="ewp0-contradiction-002",
            claim_id="ewp0-claim-002",
            participant_source_ids=["ewp0-source-003"],
            conflict_class="RETRACTION_CONFLICT",
            quarantine_signal=True,
        )
    )
    contradiction_packets = [
        build_contradiction_review_packet(
            packet_id="ewp0-contradiction-packet-001",
            claim_id="ewp0-claim-002",
            contradiction_record_ids=["ewp0-contradiction-002"],
            cluster_id="ewp0-cluster-001",
        )
    ]
    review_statuses = [
        build_packet_review_status(
            status_id="ewp0-status-001",
            packet_id="ewp0-claim-packet-001",
            claim_id="ewp0-claim-001",
            review_status="REVIEW_READY",
        ),
        build_packet_review_status(
            status_id="ewp0-status-002",
            packet_id="ewp0-contradiction-packet-001",
            claim_id="ewp0-claim-002",
            review_status="BLOCKED_BY_CONFLICT",
        ),
    ]
    dashboard = build_operator_packet_dashboard(
        dashboard_id="ewp0-dashboard-001",
        claim_packet_count=1,
        second_source_result_count=1,
        contradiction_packet_count=1,
        review_status_summary={"REVIEW_READY": 1, "BLOCKED_BY_CONFLICT": 1},
    )
    return {
        "evidence_workbench_packets": [workbench],
        "claim_evidence_packets": [claim],
        "packet_source_summaries": summaries,
        "packet_support_records": supports,
        "packet_contradiction_records": contradictions,
        "packet_second_source_requirements": requirements,
        "packet_second_source_results": second_source_results,
        "contradiction_review_packets": contradiction_packets,
        "packet_review_statuses": review_statuses,
        "operator_packet_dashboard": dashboard,
    }
