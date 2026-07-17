"""EWP-2 second-source gate tests."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.gate import validate_ewp2_gate
from hg_runtime.evidence_workbench_packets.independence_policy import all_outcomes_exercised
from hg_runtime.evidence_workbench_packets.redaction import secret_scan
from hg_runtime.evidence_workbench_packets.schemas import PHASE19_VERDICT, PHASE24_STATUS, SECOND_SOURCE_OUTCOMES
from hg_runtime.evidence_workbench_packets.second_source_gate import build_second_source_gate_layer


def _records():
    return build_second_source_gate_layer()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_EWP_2_SECOND_SOURCE_GATE",
        "reviewed_beta_green": True,
        "ewp0_green": True,
        "ewp1_green": True,
        "claim_packets_consumed": True,
        "requirements_written": True,
        "results_written": True,
        "all_outcomes_exercised": True,
        "second_source_not_truth": True,
        "second_source_missing_not_false": True,
        "duplicate_not_corroboration": True,
        "independent_not_certainty": True,
        "review_ready_not_approval": True,
        "no_belief_promotion": True,
        "no_tools_actions_live_effects": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_result_hashes": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ewp2_exercises_all_outcomes():
    outcomes = {row["outcome"] for row in _records()["packet_second_source_results"]}
    assert SECOND_SOURCE_OUTCOMES <= outcomes
    assert all_outcomes_exercised(outcomes) is True


def test_ewp2_second_source_is_not_truth():
    rows = _records()["packet_second_source_results"]
    assert all(not row["second_source_result_treated_as_truth"] for row in rows)


def test_ewp2_review_ready_is_not_approval():
    rows = _records()["packet_second_source_results"]
    assert all(not row["dashboard_treated_as_operator_approval"] for row in rows)


def test_ewp2_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_ewp2_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_ewp2_gate_passes():
    assert validate_ewp2_gate(_summary())["ok"] is True


def test_ewp2_gate_refuses_second_source_as_truth():
    assert validate_ewp2_gate(_summary(second_source_result_treated_as_truth=True))["ok"] is False
