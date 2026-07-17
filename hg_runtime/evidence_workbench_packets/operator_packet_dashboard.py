"""EWP-4 operator packet dashboard builder."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.claim_packet_builder import build_claim_evidence_packets, build_ewp1_inputs
from hg_runtime.evidence_workbench_packets.contradiction_packet_builder import build_contradiction_review_layer
from hg_runtime.evidence_workbench_packets.dashboard_summary import render_dashboard_markdown, summarize_review_statuses
from hg_runtime.evidence_workbench_packets.operator_dashboard import (
    build_operator_packet_dashboard,
    build_packet_review_status,
)
from hg_runtime.evidence_workbench_packets.second_source_gate import build_second_source_gate_layer


def _review_status_for_outcome(outcome: str) -> str:
    mapping = {
        "SECOND_SOURCE_PRESENT_REVIEW_READY": "REVIEW_READY",
        "SECOND_SOURCE_NOT_REQUIRED": "REVIEW_READY",
        "SECOND_SOURCE_REQUIRED_MISSING": "SECOND_SOURCE_REQUIRED",
        "SECOND_SOURCE_PRESENT_BUT_DUPLICATE": "SECOND_SOURCE_REQUIRED",
        "SECOND_SOURCE_PRESENT_BUT_NOT_INDEPENDENT": "SECOND_SOURCE_REQUIRED",
        "BLOCKED_BY_CONFLICT": "BLOCKED_BY_CONFLICT",
        "BLOCKED_BY_QUARANTINE": "BLOCKED_BY_QUARANTINE",
        "BLOCKED_BY_FEVER": "BLOCKED_BY_FEVER",
        "BLOCKED_BY_REDACTION": "BLOCKED_BY_REDACTION",
    }
    return mapping[outcome]


def build_operator_dashboard_layer() -> dict:
    claim_layer = build_claim_evidence_packets(build_ewp1_inputs())
    second_source_layer = build_second_source_gate_layer()
    contradiction_layer = build_contradiction_review_layer()

    review_statuses: list[dict] = []
    for idx, (req, result) in enumerate(
        zip(
            second_source_layer["packet_second_source_requirements"],
            second_source_layer["packet_second_source_results"],
            strict=True,
        ),
        start=1,
    ):
        review_statuses.append(
            build_packet_review_status(
                status_id=f"ewp4-status-ss-{idx:03d}",
                packet_id=result["packet_id"],
                claim_id=req["claim_id"],
                review_status=_review_status_for_outcome(result["outcome"]),
            )
        )

    for idx, packet in enumerate(contradiction_layer["contradiction_review_packets"], start=1):
        review_statuses.append(
            build_packet_review_status(
                status_id=f"ewp4-status-contradiction-{idx:03d}",
                packet_id=packet["packet_id"],
                claim_id=packet["claim_id"],
                review_status="BLOCKED_BY_CONFLICT",
            )
        )

    for idx, packet in enumerate(claim_layer["claim_evidence_packets"], start=1):
        status = "BLOCKED_BY_CONFLICT" if packet["contradiction_record_ids"] else "PENDING_REVIEW"
        review_statuses.append(
            build_packet_review_status(
                status_id=f"ewp4-status-claim-{idx:03d}",
                packet_id=packet["packet_id"],
                claim_id=packet["claim_id"],
                review_status=status,
            )
        )

    status_summary = summarize_review_statuses(review_statuses)
    dashboard = build_operator_packet_dashboard(
        dashboard_id="ewp4-dashboard-001",
        claim_packet_count=len(claim_layer["claim_evidence_packets"]),
        second_source_result_count=len(second_source_layer["packet_second_source_results"]),
        contradiction_packet_count=len(contradiction_layer["contradiction_review_packets"]),
        review_status_summary=status_summary,
    )
    dashboard_md = render_dashboard_markdown(dashboard, review_statuses)

    return {
        "operator_packet_dashboard": dashboard,
        "operator_packet_dashboard_md": dashboard_md,
        "packet_review_statuses": review_statuses,
        "claim_evidence_packets": claim_layer["claim_evidence_packets"],
        "packet_second_source_results": second_source_layer["packet_second_source_results"],
        "contradiction_review_packets": contradiction_layer["contradiction_review_packets"],
    }
