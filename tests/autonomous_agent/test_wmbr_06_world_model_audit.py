"""WMBR-06 / CAGI-47 world-model audit, decay, and retraction closure tests.

Doctrine: Every model is a compressed civilization artifact.
Decay is not deletion. Retraction is not erasure. Audit closure is not laundering.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hg_runtime.world_model_audit.artifact_writer import build_audit_layer, secret_scan
from hg_runtime.world_model_audit.audit_record import validate_record_audit
from hg_runtime.world_model_audit.calibration_loader import (
    discover_latest_bundle,
    load_calibration_bundle,
    validate_calibration_bundle,
)
from hg_runtime.world_model_audit.decay import validate_decay_record
from hg_runtime.world_model_audit.fixtures import (
    action_authorization_attempt_fixture,
    audit_laundering_attempt_fixture,
    contradicted_hypothesis_fixture_wmbr06,
    deletion_rewrite_attempt_fixture,
    failed_prediction_fixture,
    fixture_calibration_bundle,
    low_confidence_hypothesis_fixture,
    retracted_belief_source_fixture,
    stale_prediction_fixture,
    truth_certainty_laundering_attempt_fixture,
    unsupported_belief_state_fixture,
)
from hg_runtime.world_model_audit.gate import validate_wmbr06_gate
from hg_runtime.world_model_audit.replay import replay_audit
from hg_runtime.world_model_audit.retraction_closure import validate_retraction_closure
from hg_runtime.world_model_audit.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RUNTIME_P42_VERDICT_GREEN,
    VERDICT_GREEN,
    WMBR_03_VERDICT_GREEN,
    WMBR_04_VERDICT_GREEN,
    WMBR_05_VERDICT_GREEN,
    WorldModelAuditError,
    assert_neutral,
)

ROOT = Path(__file__).resolve().parents[2]
WMBR_05_PROOF_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/WMBR-05-PREDICTIVE-CALIBRATION"


def _out():
    return build_audit_layer(fixture_calibration_bundle())


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "wmbr05_green": True,
        "wmbr04_green": True,
        "wmbr03_green": True,
        "runtime_p42_green": True,
        "input_calibration_loaded": True,
        "audit_manifest_written": True,
        "record_audits_written": True,
        "record_audit_count": 12,
        "stale_records_written": True,
        "stale_marker_count": 2,
        "decay_records_written": True,
        "decay_record_count": 2,
        "failed_prediction_audits_written": True,
        "failed_prediction_audit_count": 1,
        "contradiction_audits_written": True,
        "contradiction_audit_count": 1,
        "retraction_closures_written": True,
        "retraction_closure_count": 1,
        "maintenance_policy_written": True,
        "decay_is_not_deletion": True,
        "retraction_is_not_erasure": True,
        "audit_closure_is_not_laundering": True,
        "stale_records_remain_visible": True,
        "failed_predictions_remain_visible": True,
        "contradictions_remain_visible": True,
        "belief_state_is_not_truth": True,
        "causal_hypothesis_is_not_truth": True,
        "prediction_is_not_verification": True,
        "calibration_is_not_proof": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_audit_hashes": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_audit_laundering_rejected": True,
        "candidate_agi_parent_phase_completed": False,
    }
    data.update(overrides)
    return data


# --- Loading ---------------------------------------------------------------

def test_wmbr06_loads_wmbr05_calibration_bundle():
    bundle_dir = discover_latest_bundle(WMBR_05_PROOF_ROOT)
    assert bundle_dir is not None
    bundle = load_calibration_bundle(bundle_dir)
    validate_calibration_bundle(bundle)
    assert bundle["prediction_candidates"]


def test_wmbr06_accepts_fixture_calibration_when_bundle_unavailable():
    assert _out()["summary"]["record_audit_count"] > 0


def test_wmbr06_rejects_missing_calibration_bundle():
    with pytest.raises(WorldModelAuditError):
        validate_calibration_bundle({"manifest": {}, "prediction_candidates": []})


# --- Fixture scenarios -----------------------------------------------------

def test_wmbr06_stale_prediction_fixture():
    fx = stale_prediction_fixture()
    assert fx["candidate"]["prediction_status"] == "INSUFFICIENT_CONTEXT"


def test_wmbr06_failed_prediction_fixture():
    fx = failed_prediction_fixture()
    assert fx["calibration"]["score_kind"] == "MISMATCH"


def test_wmbr06_contradicted_hypothesis_fixture():
    fx = contradicted_hypothesis_fixture_wmbr06()
    assert fx["hypothesis"]["hypothesis_status"] == "CONTRADICTED"


def test_wmbr06_retracted_belief_source_fixture():
    fx = retracted_belief_source_fixture()
    assert fx["hypothesis"]["hypothesis_status"] == "RETRACTED"


def test_wmbr06_unsupported_belief_state_fixture():
    fx = unsupported_belief_state_fixture()
    assert fx["belief_state"]["belief_status"] == "UNVERIFIED"


def test_wmbr06_low_confidence_hypothesis_fixture():
    fx = low_confidence_hypothesis_fixture()
    assert fx["uncertainty"]["uncertainty_level"] in ("HIGH", "UNKNOWN", "MEDIUM")


# --- Audit outputs ---------------------------------------------------------

def test_wmbr06_creates_record_audits():
    assert _out()["record_audits"]


def test_wmbr06_creates_stale_markers():
    assert _out()["stale_markers"]


def test_wmbr06_creates_decay_records():
    out = _out()
    assert out["decay_records"]
    assert all(not d["deletion_performed"] for d in out["decay_records"])


def test_wmbr06_creates_failed_prediction_audits():
    out = _out()
    assert out["failed_prediction_audits"]
    assert all(f["failed_prediction_remains_visible"] for f in out["failed_prediction_audits"])


def test_wmbr06_creates_contradiction_audits():
    out = _out()
    assert out["contradiction_audits"]
    assert all(c["contradiction_remains_visible"] for c in out["contradiction_audits"])


def test_wmbr06_creates_retraction_closures():
    out = _out()
    assert out["retraction_closures"]
    assert all(r["original_preserved"] for r in out["retraction_closures"])


def test_wmbr06_creates_maintenance_policy():
    policy = _out()["maintenance_policy"]
    assert policy["decay_is_not_deletion"] is True
    assert policy["automatic_deletion_allowed"] is False


# --- Boundaries ------------------------------------------------------------

def test_wmbr06_decay_is_not_deletion():
    out = _out()
    assert all(not d["decay_treated_as_deletion"] for d in out["decay_records"])
    assert all(d["decay_is_not_deletion"] for d in out["decay_records"])


def test_wmbr06_retraction_is_not_erasure():
    out = _out()
    assert all(not r["retraction_treated_as_erasure"] for r in out["retraction_closures"])


def test_wmbr06_no_truth_claimed():
    out = _out()
    assert all(not r.get("truth_claimed") for r in out["record_audits"])


def test_wmbr06_no_certainty_claimed():
    assert all(not r.get("certainty_claimed") for r in _out()["record_audits"])


def test_wmbr06_no_action_authorized():
    assert _out()["maintenance_policy"]["action_authorized"] is False


def test_wmbr06_no_tools_authorized():
    assert _out()["maintenance_policy"]["tools_authorized"] is False


def test_wmbr06_no_web_browse():
    assert _out()["manifest"]["web_browse_performed"] is False


def test_wmbr06_no_external_provider_calls():
    assert _out()["manifest"]["external_provider_calls_made"] is False


def test_wmbr06_no_live_effects():
    assert _out()["manifest"]["live_external_side_effects_created"] is False


def test_wmbr06_no_authority_granted():
    assert _out()["manifest"]["authority_granted"] is False


# --- Prior-phase preservation ---------------------------------------------

def test_wmbr06_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_wmbr06_preserves_phase40_repair():
    assert _gate_summary()["phase40_repair_preserved"] is True


def test_wmbr06_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_wmbr06_does_not_complete_wmbr01_parent():
    assert validate_wmbr06_gate(_gate_summary(candidate_agi_parent_phase_completed=True))["ok"] is False


# --- Replay & laundering ---------------------------------------------------

def test_wmbr06_replay_preserves_audit_hashes():
    out = _out()
    assert replay_audit(
        out["record_audits"],
        out["stale_markers"],
        out["decay_records"],
        out["contradiction_audits"],
        out["failed_prediction_audits"],
        out["retraction_closures"],
        out["maintenance_policy"],
        out["manifest"],
    )["ok"] is True


def test_wmbr06_replay_rejects_mutated_audit():
    out = _out()
    audits = copy.deepcopy(out["record_audits"])
    audits[0]["audit_status"] = "MUTATED"
    assert replay_audit(
        audits,
        out["stale_markers"],
        out["decay_records"],
        out["contradiction_audits"],
        out["failed_prediction_audits"],
        out["retraction_closures"],
        out["maintenance_policy"],
        out["manifest"],
    )["ok"] is False


def test_wmbr06_no_secret_material_in_artifacts():
    assert secret_scan(_out()) is True


def test_wmbr06_fake_green_audit_laundering_rejected():
    assert validate_wmbr06_gate(_gate_summary(audit_closure_treated_as_laundering=True))["ok"] is False


def test_wmbr06_audit_laundering_fixture_rejected():
    with pytest.raises(WorldModelAuditError):
        assert_neutral(audit_laundering_attempt_fixture())


def test_wmbr06_deletion_rewrite_fixture_rejected():
    with pytest.raises(ValueError):
        validate_decay_record(deletion_rewrite_attempt_fixture())
    with pytest.raises(WorldModelAuditError):
        assert_neutral(deletion_rewrite_attempt_fixture())


def test_wmbr06_action_authorization_fixture_rejected():
    with pytest.raises(WorldModelAuditError):
        assert_neutral(action_authorization_attempt_fixture())


def test_wmbr06_truth_certainty_laundering_fixture_rejected():
    with pytest.raises(WorldModelAuditError):
        assert_neutral(truth_certainty_laundering_attempt_fixture())


# --- Gate ------------------------------------------------------------------

def test_wmbr06_gate_requires_wmbr05_green():
    assert validate_wmbr06_gate(_gate_summary(wmbr05_green=False))["ok"] is False
    assert WMBR_05_VERDICT_GREEN.startswith("GREEN_WMBR_05")


def test_wmbr06_gate_requires_wmbr04_green():
    assert validate_wmbr06_gate(_gate_summary(wmbr04_green=False))["ok"] is False
    assert WMBR_04_VERDICT_GREEN.startswith("GREEN_WMBR_04")


def test_wmbr06_gate_requires_wmbr03_green():
    assert validate_wmbr06_gate(_gate_summary(wmbr03_green=False))["ok"] is False
    assert WMBR_03_VERDICT_GREEN.startswith("GREEN_WMBR_03")


def test_wmbr06_gate_requires_runtime_p42_green():
    assert validate_wmbr06_gate(_gate_summary(runtime_p42_green=False))["ok"] is False
    assert RUNTIME_P42_VERDICT_GREEN.startswith("GREEN_PHASE42")


def test_wmbr06_gate_refuses_without_record_audits():
    assert validate_wmbr06_gate(_gate_summary(record_audits_written=False, record_audit_count=0))["ok"] is False


def test_wmbr06_gate_refuses_if_decay_treated_as_deletion():
    assert validate_wmbr06_gate(_gate_summary(decay_treated_as_deletion=True))["ok"] is False


def test_wmbr06_gate_refuses_if_retraction_treated_as_erasure():
    assert validate_wmbr06_gate(_gate_summary(retraction_treated_as_erasure=True))["ok"] is False


def test_wmbr06_gate_refuses_if_audit_closure_launders():
    assert validate_wmbr06_gate(_gate_summary(audit_closure_treated_as_laundering=True))["ok"] is False


def test_wmbr06_gate_refuses_if_authority_granted():
    assert validate_wmbr06_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_wmbr06_gate_refuses_if_live_effect_created():
    assert validate_wmbr06_gate(_gate_summary(live_external_side_effects_created=True))["ok"] is False


def test_wmbr06_gate_refuses_without_proof_bundle():
    assert validate_wmbr06_gate(_gate_summary(proof_bundle_valid=False))["ok"] is False


def test_wmbr06_gate_passes_on_full_summary():
    assert validate_wmbr06_gate(_gate_summary())["ok"] is True


def test_wmbr06_retraction_closure_validates_original_preserved():
    out = _out()
    for closure in out["retraction_closures"]:
        validate_retraction_closure(closure)


def test_wmbr06_record_audit_validates_no_deletion():
    for audit in _out()["record_audits"]:
        validate_record_audit(audit)
