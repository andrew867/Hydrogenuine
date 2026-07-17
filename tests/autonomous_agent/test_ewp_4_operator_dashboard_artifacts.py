"""EWP-4 operator dashboard artifact tests."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.gate import validate_ewp4_gate
from hg_runtime.evidence_workbench_packets.operator_packet_dashboard import build_operator_dashboard_layer
from hg_runtime.evidence_workbench_packets.redaction import secret_scan
from hg_runtime.evidence_workbench_packets.schemas import PHASE19_VERDICT, PHASE24_STATUS


def _records():
    return build_operator_dashboard_layer()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_EWP_4_OPERATOR_PACKET_DASHBOARD",
        "reviewed_beta_green": True,
        "ewp1_green": True,
        "ewp2_green": True,
        "ewp3_green": True,
        "claim_packets_consumed": True,
        "second_source_results_consumed": True,
        "contradiction_packets_consumed": True,
        "dashboard_written": True,
        "dashboard_md_written": True,
        "review_statuses_written": True,
        "dashboard_not_approval": True,
        "dashboard_not_truth": True,
        "dashboard_cannot_authorize_action": True,
        "dashboard_cannot_authorize_tool": True,
        "dashboard_cannot_promote_belief": True,
        "dashboard_cannot_hide_contradictions": True,
        "dashboard_cannot_delete": True,
        "no_live_ui": True,
        "no_belief_promotion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_dashboard_hash": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ewp4_builds_dashboard():
    records = _records()
    assert records["operator_packet_dashboard"]["record_type"] == "operator_packet_dashboard_v1"
    assert records["operator_packet_dashboard_md"]
    assert records["packet_review_statuses"]


def test_ewp4_dashboard_is_not_approval():
    dashboard = _records()["operator_packet_dashboard"]
    assert dashboard["dashboard_treated_as_operator_approval"] is False


def test_ewp4_dashboard_cannot_authorize():
    dashboard = _records()["operator_packet_dashboard"]
    assert dashboard["authority_granted"] is False
    assert dashboard["tools_authorized"] is False
    assert dashboard["belief_promotion_automatic"] is False


def test_ewp4_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_ewp4_gate_passes():
    assert validate_ewp4_gate(_summary())["ok"] is True


def test_ewp4_gate_refuses_dashboard_as_approval():
    assert validate_ewp4_gate(_summary(dashboard_treated_as_operator_approval=True))["ok"] is False
