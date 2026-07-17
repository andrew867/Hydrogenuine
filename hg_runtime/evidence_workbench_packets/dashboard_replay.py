"""Replay EWP-4 dashboard building."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.operator_packet_dashboard import build_operator_dashboard_layer
from hg_runtime.evidence_workbench_packets.schemas import record_hash


def replay_dashboard_build(
    *,
    expected_manifest_hash: str,
    expected_dashboard_hash: str,
) -> dict:
    records = build_operator_dashboard_layer()
    dashboard = records["operator_packet_dashboard"]
    manifest_hash = record_hash(
        {
            "dashboard": dashboard,
            "statuses": records["packet_review_statuses"],
        }
    )
    return {
        "replay_preserves_dashboard_hash": dashboard["dashboard_hash"] == expected_dashboard_hash,
        "replay_preserves_manifest_hash": manifest_hash == expected_manifest_hash,
        "manifest_hash": manifest_hash,
        "dashboard_hash": dashboard["dashboard_hash"],
    }
