"""EWP-0 schema foundation tests."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.fixtures import build_ewp0_fixture_records
from hg_runtime.evidence_workbench_packets.gate import validate_ewp0_gate
from hg_runtime.evidence_workbench_packets.redaction import secret_scan
from hg_runtime.evidence_workbench_packets.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RECORD_TYPES,
    SECOND_SOURCE_OUTCOMES,
)


def _records():
    return build_ewp0_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_EWP_0_SCHEMA_FOUNDATION",
        "reviewed_beta_green": True,
        "sqp_consolidation_green": True,
        "schemas_declared": True,
        "workbench_packet_written": True,
        "claim_packet_written": True,
        "source_summary_written": True,
        "support_record_written": True,
        "contradiction_record_written": True,
        "second_source_requirement_written": True,
        "second_source_result_written": True,
        "contradiction_review_packet_written": True,
        "review_status_written": True,
        "dashboard_written": True,
        "packet_not_truth": True,
        "packet_not_authority": True,
        "packet_not_approval": True,
        "support_not_proof": True,
        "contradiction_not_resolution": True,
        "second_source_not_truth": True,
        "dashboard_not_approval": True,
        "no_belief_promotion": True,
        "no_authority": True,
        "no_tools": True,
        "no_live_effects": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ewp0_declares_required_record_types():
    expected = {
        "evidence_workbench_packet_v1",
        "claim_evidence_packet_v1",
        "packet_source_summary_v1",
        "packet_support_record_v1",
        "packet_contradiction_record_v1",
        "packet_second_source_requirement_v1",
        "packet_second_source_result_v1",
        "contradiction_review_packet_v1",
        "operator_packet_dashboard_v1",
        "packet_review_status_v1",
        "packet_gate_result_v1",
    }
    assert expected <= RECORD_TYPES


def test_ewp0_builds_all_schema_records():
    records = _records()
    assert records["evidence_workbench_packets"]
    assert records["claim_evidence_packets"]
    assert records["packet_source_summaries"]
    assert records["packet_support_records"]
    assert records["packet_contradiction_records"]
    assert records["packet_second_source_requirements"]
    assert records["packet_second_source_results"]
    assert records["contradiction_review_packets"]
    assert records["packet_review_statuses"]
    assert records["operator_packet_dashboard"]


def test_ewp0_second_source_outcomes_declared():
    assert "SECOND_SOURCE_PRESENT_REVIEW_READY" in SECOND_SOURCE_OUTCOMES
    assert "BLOCKED_BY_FEVER" in SECOND_SOURCE_OUTCOMES


def test_ewp0_packet_is_not_truth():
    rows = [item for value in _records().values() for item in (value if isinstance(value, list) else [value])]
    assert all(not row["packet_treated_as_truth"] for row in rows)


def test_ewp0_support_is_not_proof():
    assert all(not row["support_record_treated_as_proof"] for row in _records()["packet_support_records"])


def test_ewp0_contradiction_is_not_resolution():
    assert all(not row["contradiction_record_treated_as_resolution"] for row in _records()["packet_contradiction_records"])


def test_ewp0_second_source_is_not_truth():
    assert all(not row["second_source_result_treated_as_truth"] for row in _records()["packet_second_source_results"])


def test_ewp0_dashboard_is_not_approval():
    dashboard = _records()["operator_packet_dashboard"]
    assert dashboard["dashboard_treated_as_operator_approval"] is False


def test_ewp0_no_belief_promotion_authority_tools_live_effects():
    rows = [item for value in _records().values() for item in (value if isinstance(value, list) else [value])]
    assert all(not row["belief_promotion_automatic"] for row in rows)
    assert all(not row["authority_granted"] for row in rows)
    assert all(not row["tools_authorized"] for row in rows)
    assert all(not row["live_external_side_effects_created"] for row in rows)


def test_ewp0_no_web_or_provider():
    rows = [item for value in _records().values() for item in (value if isinstance(value, list) else [value])]
    assert all(not row["web_browse_performed"] for row in rows)
    assert all(not row["external_provider_calls_made"] for row in rows)


def test_ewp0_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_ewp0_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_ewp0_gate_passes_full_summary():
    assert validate_ewp0_gate(_summary())["ok"] is True


def test_ewp0_gate_refuses_packet_as_truth():
    assert validate_ewp0_gate(_summary(packet_treated_as_truth=True))["ok"] is False


def test_ewp0_gate_refuses_dashboard_as_approval():
    assert validate_ewp0_gate(_summary(dashboard_treated_as_operator_approval=True))["ok"] is False


def test_ewp0_gate_refuses_belief_promotion():
    assert validate_ewp0_gate(_summary(belief_promotion_automatic=True))["ok"] is False
