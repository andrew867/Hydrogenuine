"""DTX operator dashboard evaluation helpers."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.dashboard_summary import render_dashboard_markdown, summarize_review_statuses
from hg_runtime.evidence_workbench_packets.operator_dashboard import build_operator_packet_dashboard


def build_dashboard(*, claim_packets: list[dict], second_source_results: list[dict], contradiction_packets: list[dict], review_statuses: list[dict]) -> tuple[dict, str]:
    status_summary = summarize_review_statuses(review_statuses)
    dashboard = build_operator_packet_dashboard(
        dashboard_id="dtx-document-dashboard-001",
        claim_packet_count=len(claim_packets),
        second_source_result_count=len(second_source_results),
        contradiction_packet_count=len(contradiction_packets),
        review_status_summary=status_summary,
    )
    return dashboard, render_dashboard_markdown(dashboard, review_statuses)
