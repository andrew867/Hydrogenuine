"""LHRE-03 / CAGI-56 external evaluation vessel tests.

An external evaluation result is not truth. An evaluation vessel is not deployment permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.external_evaluation_vessel.artifact_writer import build_vessel_artifacts, secret_scan
from hg_runtime.external_evaluation_vessel.fixtures import (
    fixture_evaluation_vessels, fixture_evaluator_provenance,
    fixture_task_bundles, fixture_vessel_authority_attempt, fixture_vessel_results,
)
from hg_runtime.external_evaluation_vessel.gate import validate_lhre03_gate
from hg_runtime.external_evaluation_vessel.replay import replay_vessel_artifacts
from hg_runtime.external_evaluation_vessel.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    EvaluationVesselError, reject_vessel_authority,
)
from hg_runtime.external_evaluation_vessel.vessel import validate_result, validate_vessel


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "LHRE_03" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_vessels_sealed():
    for v in fixture_evaluation_vessels():
        assert v["upload_to_network"] is False
        assert v["send_to_evaluator"] is False

def test_fixture_results_not_truth():
    for r in fixture_vessel_results():
        assert r["is_truth"] is False
        assert r["is_competence"] is False

def test_validate_vessel_valid():
    assert validate_vessel(fixture_evaluation_vessels()[0]) == []

def test_validate_vessel_rejects_upload():
    with pytest.raises(EvaluationVesselError):
        validate_vessel(fixture_vessel_authority_attempt())

def test_validate_result_valid():
    assert validate_result(fixture_vessel_results()[0]) == []

def test_validate_result_rejects_truth():
    issues = validate_result({"is_truth": True})
    assert "result_must_not_claim_truth" in issues

def test_validate_result_rejects_competence():
    issues = validate_result({"is_competence": True})
    assert "result_must_not_claim_competence" in issues

def test_reject_vessel_authority_clean():
    reject_vessel_authority({"sealed": True})

def test_reject_vessel_upload():
    with pytest.raises(EvaluationVesselError):
        reject_vessel_authority({"upload_to_network": True})

def test_reject_vessel_send():
    with pytest.raises(EvaluationVesselError):
        reject_vessel_authority({"send_to_evaluator": True})

def test_reject_vessel_agi():
    with pytest.raises(EvaluationVesselError):
        reject_vessel_authority({"claims_agi": True})

def test_reject_vessel_deployment():
    with pytest.raises(EvaluationVesselError):
        reject_vessel_authority({"deployment_permission": True})

def test_build_vessel_artifacts():
    artifacts = build_vessel_artifacts(
        fixture_evaluation_vessels(), fixture_task_bundles(),
        fixture_evaluator_provenance(), fixture_vessel_results(),
    )
    assert artifacts["vessel_count"] == 2
    assert artifacts["all_vessels_sealed"] is True
    assert artifacts["all_results_not_truth"] is True
    assert artifacts["no_network_uploads"] is True
    assert "artifact_hash" in artifacts

def test_build_rejects_authority():
    with pytest.raises(EvaluationVesselError):
        build_vessel_artifacts([fixture_vessel_authority_attempt()], [], [], [])

def test_secret_scan_clean():
    artifacts = build_vessel_artifacts(
        fixture_evaluation_vessels(), fixture_task_bundles(),
        fixture_evaluator_provenance(), fixture_vessel_results(),
    )
    assert secret_scan(artifacts) == []

def test_replay_deterministic():
    a = replay_vessel_artifacts()
    b = replay_vessel_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "lhre02_green": True,
        "vessels_written": True, "bundles_written": True,
        "provenance_written": True, "results_written": True,
        "all_vessels_sealed": True, "all_results_not_truth": True,
        "no_network_uploads": True, "safety_boundaries_enforced": True,
        "reject_vessel_authority_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_vessel_authority_rejected": True,
        "network_upload_performed": False, "sent_to_evaluator": False,
        "tool_authorized": False, "authority_granted": False,
        "live_effect_created": False, "agi_claimed": False,
        "deployment_permission_granted": False, "eval_treated_as_competence": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_lhre03_gate(_gate_summary())["ok"] is True

def test_gate_rejects_upload():
    assert validate_lhre03_gate(_gate_summary(network_upload_performed=True))["ok"] is False

def test_gate_rejects_authority():
    assert validate_lhre03_gate(_gate_summary(authority_granted=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_lhre03_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_deployment():
    assert validate_lhre03_gate(_gate_summary(deployment_permission_granted=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_lhre03_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
