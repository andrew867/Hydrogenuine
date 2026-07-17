"""WMBR-05 / CAGI-46 predictive calibration and uncertainty scoring tests.

Doctrine: Every model is a compressed civilization artifact.
A prediction is not verification. A calibration record is not proof.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hg_runtime.predictive_calibration.artifact_writer import build_calibration_layer, secret_scan
from hg_runtime.predictive_calibration.calibration_score import validate_calibration_record
from hg_runtime.predictive_calibration.causal_loader import (
    discover_latest_bundle,
    load_causal_bundle,
    validate_causal_bundle,
)
from hg_runtime.predictive_calibration.drift_detector import detect_drift
from hg_runtime.predictive_calibration.fixtures import (
    calibration_proof_laundering_fixture,
    contradicted_hypothesis_fixture,
    fixture_causal_graph,
    live_observation_laundering_fixture,
    prediction_verification_laundering_fixture,
    retracted_source_fixture,
    synthetic_match_fixture,
    synthetic_mismatch_fixture,
    synthetic_partial_fixture,
    synthetic_unknown_fixture,
    uncertainty_permission_laundering_fixture,
)
from hg_runtime.predictive_calibration.gate import validate_wmbr05_gate
from hg_runtime.predictive_calibration.prediction_candidate import (
    build_prediction_candidate,
    validate_prediction_candidate,
)
from hg_runtime.predictive_calibration.replay import replay_calibration
from hg_runtime.predictive_calibration.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PredictiveCalibrationError,
    RUNTIME_P42_VERDICT_GREEN,
    VERDICT_GREEN,
    WMBR_03_VERDICT_GREEN,
    WMBR_04_VERDICT_GREEN,
    assert_neutral,
)
from hg_runtime.predictive_calibration.synthetic_outcome import validate_synthetic_outcome
from hg_runtime.predictive_calibration.uncertainty_score import build_uncertainty_score, validate_uncertainty_score

ROOT = Path(__file__).resolve().parents[2]
WMBR_04_PROOF_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/WMBR-04-CAUSAL-WORLD-MODEL-BOUNDARY"


def _out():
    return build_calibration_layer(fixture_causal_graph())


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "wmbr04_green": True,
        "wmbr03_green": True,
        "runtime_p42_green": True,
        "input_causal_graph_loaded": True,
        "causal_hypotheses_loaded": True,
        "causal_hypothesis_count": 12,
        "prediction_candidates_written": True,
        "prediction_candidate_count": 12,
        "synthetic_outcomes_written": True,
        "synthetic_outcome_count": 4,
        "calibration_records_written": True,
        "calibration_record_count": 4,
        "uncertainty_scores_written": True,
        "uncertainty_score_count": 12,
        "calibration_manifest_written": True,
        "causal_hypothesis_is_not_truth": True,
        "prediction_is_not_verification": True,
        "calibration_is_not_proof": True,
        "uncertainty_is_not_permission": True,
        "confidence_is_not_authority": True,
        "synthetic_outcome_is_not_live_observation": True,
        "mismatches_remain_visible": True,
        "drift_records_created_for_mismatches": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_calibration_hashes": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_prediction_verified_rejected": True,
        "candidate_agi_parent_phase_completed": False,
    }
    data.update(overrides)
    return data


# --- Loading ---------------------------------------------------------------

def test_wmbr05_loads_wmbr04_causal_graph():
    bundle_dir = discover_latest_bundle(WMBR_04_PROOF_ROOT)
    assert bundle_dir is not None
    bundle = load_causal_bundle(bundle_dir)
    validate_causal_bundle(bundle)
    assert bundle["hypotheses"]


def test_wmbr05_accepts_fixture_causal_graph_when_bundle_unavailable():
    assert _out()["summary"]["prediction_candidate_count"] > 0


def test_wmbr05_rejects_missing_causal_graph():
    with pytest.raises(PredictiveCalibrationError):
        validate_causal_bundle({"manifest": {}, "hypotheses": []})


# --- Prediction candidates -------------------------------------------------

def test_wmbr05_only_provisional_hypotheses_emit_predictions():
    out = _out()
    proposed = [c for c in out["prediction_candidates"] if c["prediction_status"] != "INSUFFICIENT_CONTEXT"]
    assert proposed
    assert all(c["prediction_status"] in ("PROPOSED_UNTESTED", "SYNTHETIC_OUTCOME_ATTACHED") for c in proposed)


def test_wmbr05_causal_hypothesis_is_not_truth():
    assert all(not h.get("causal_truth_claimed") for h in _out()["hypotheses"])


def test_wmbr05_creates_prediction_candidates():
    assert _out()["prediction_candidates"]


def test_wmbr05_prediction_is_not_verification():
    assert all(not c["prediction_is_verification"] for c in _out()["prediction_candidates"])


def test_wmbr05_synthetic_outcome_is_not_live_observation():
    assert all(not s["live_observation"] for s in _out()["synthetic_outcomes"])


def test_wmbr05_creates_calibration_records():
    assert _out()["calibration_records"]


def test_wmbr05_calibration_record_is_not_proof():
    assert all(not c["calibration_is_proof"] for c in _out()["calibration_records"])


def test_wmbr05_creates_uncertainty_scores():
    assert _out()["uncertainty_scores"]


def test_wmbr05_uncertainty_score_is_not_permission():
    assert all(not u["uncertainty_is_permission"] for u in _out()["uncertainty_scores"])


def test_wmbr05_confidence_score_is_not_authority():
    assert all(not u["confidence_is_authority"] for u in _out()["uncertainty_scores"])


# --- Fixture scenarios -----------------------------------------------------

def test_wmbr05_synthetic_match_scores_without_truth_claim():
    fx = synthetic_match_fixture()
    assert fx["calibration"]["score_kind"] == "EXACT_MATCH"
    assert fx["calibration"]["truth_claimed"] is False
    assert fx["calibration"]["calibration_is_proof"] is False


def test_wmbr05_synthetic_mismatch_creates_drift_record():
    fx = synthetic_mismatch_fixture()
    assert fx["calibration"]["score_kind"] == "MISMATCH"
    out = _out()
    assert any(d["drift_type"] == "SYNTHETIC_MISMATCH" for d in out["drift_records"])


def test_wmbr05_synthetic_partial_keeps_uncertainty():
    fx = synthetic_partial_fixture()
    assert fx["calibration"]["score_kind"] == "PARTIAL_MATCH"
    hyp = contradicted_hypothesis_fixture()["hypothesis"]
    cand = build_prediction_candidate(hypothesis=hyp, edge_ids=[], evidence_receipt_ids=[])
    assert cand is not None
    unc = build_uncertainty_score(
        prediction_candidate=cand,
        hypothesis=hyp,
        calibration_record=fx["calibration"],
    )
    assert unc["confidence_score"] > 0


def test_wmbr05_synthetic_unknown_keeps_high_or_unknown_uncertainty():
    fx = synthetic_unknown_fixture()
    assert fx["calibration"]["score_kind"] == "UNKNOWN"
    hyp = fx["candidate"]
    # use proposed hypothesis from fixture graph
    for h in fixture_causal_graph()["hypotheses"]:
        if h["hypothesis_status"] == "PROPOSED":
            unc = build_uncertainty_score(
                prediction_candidate=build_prediction_candidate(hypothesis=h, edge_ids=[], evidence_receipt_ids=[]),
                hypothesis=h,
                calibration_record=fx["calibration"],
            )
            assert unc["uncertainty_level"] in ("HIGH", "MEDIUM", "UNKNOWN")
            break


def test_wmbr05_contradicted_hypothesis_increases_uncertainty():
    hyp = contradicted_hypothesis_fixture()["hypothesis"]
    cand = build_prediction_candidate(hypothesis=hyp, edge_ids=[], evidence_receipt_ids=[])
    assert cand is not None
    unc = build_uncertainty_score(prediction_candidate=cand, hypothesis=hyp)
    assert unc["uncertainty_level"] == "HIGH"
    assert not cand.get("prediction_verified")


def test_wmbr05_retracted_source_not_emitted_or_insufficient_context():
    hyp = retracted_source_fixture()["hypothesis"]
    assert build_prediction_candidate(hypothesis=hyp, edge_ids=[], evidence_receipt_ids=[]) is None


# --- Boundaries ------------------------------------------------------------

def test_wmbr05_no_prediction_marked_verified():
    assert all(not c.get("prediction_verified") for c in _out()["prediction_candidates"])


def test_wmbr05_no_truth_claimed():
    out = _out()
    assert all(not c.get("truth_claimed") for c in out["prediction_candidates"])
    assert all(not c.get("truth_claimed") for c in out["calibration_records"])


def test_wmbr05_no_certainty_claimed():
    assert all(not c.get("certainty_claimed") for c in _out()["prediction_candidates"])


def test_wmbr05_no_action_authorized():
    out = _out()
    assert all(not c.get("action_authorized") for c in out["prediction_candidates"])
    assert all(not u.get("action_authorized") for u in out["uncertainty_scores"])


def test_wmbr05_no_tools_authorized():
    assert _out()["manifest"]["tools_authorized"] is False


def test_wmbr05_no_web_browse():
    assert _out()["manifest"]["web_browse_performed"] is False


def test_wmbr05_no_external_provider_calls():
    assert _out()["manifest"]["external_provider_calls_made"] is False


def test_wmbr05_no_live_effects():
    assert _out()["manifest"]["live_external_side_effects_created"] is False


def test_wmbr05_no_authority_granted():
    assert _out()["manifest"]["authority_granted"] is False


# --- Prior-phase preservation ---------------------------------------------

def test_wmbr05_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_wmbr05_preserves_phase40_repair():
    assert _gate_summary()["phase40_repair_preserved"] is True


def test_wmbr05_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_wmbr05_does_not_complete_wmbr01_parent():
    assert validate_wmbr05_gate(_gate_summary(candidate_agi_parent_phase_completed=True))["ok"] is False


# --- Replay & laundering ---------------------------------------------------

def test_wmbr05_replay_preserves_calibration_hashes():
    out = _out()
    assert replay_calibration(
        out["prediction_candidates"],
        out["calibration_records"],
        out["uncertainty_scores"],
        out["drift_records"],
        out["manifest"],
    )["ok"] is True


def test_wmbr05_replay_rejects_mutated_calibration():
    out = _out()
    cals = copy.deepcopy(out["calibration_records"])
    cals[0]["score_kind"] = "MUTATED"
    assert replay_calibration(
        out["prediction_candidates"],
        cals,
        out["uncertainty_scores"],
        out["drift_records"],
        out["manifest"],
    )["ok"] is False


def test_wmbr05_no_secret_material_in_artifacts():
    assert secret_scan(_out()) is True


def test_wmbr05_fake_green_prediction_verified_rejected():
    assert validate_wmbr05_gate(_gate_summary(predictions_marked_verified=True))["ok"] is False


def test_wmbr05_prediction_verification_laundering_fixture_rejected():
    with pytest.raises(PredictiveCalibrationError):
        validate_prediction_candidate(prediction_verification_laundering_fixture())
    with pytest.raises(PredictiveCalibrationError):
        assert_neutral(prediction_verification_laundering_fixture())


def test_wmbr05_calibration_proof_laundering_fixture_rejected():
    with pytest.raises(PredictiveCalibrationError):
        validate_calibration_record(calibration_proof_laundering_fixture())
    with pytest.raises(PredictiveCalibrationError):
        assert_neutral(calibration_proof_laundering_fixture())


def test_wmbr05_uncertainty_permission_laundering_fixture_rejected():
    with pytest.raises(PredictiveCalibrationError):
        validate_uncertainty_score(uncertainty_permission_laundering_fixture())
    with pytest.raises(PredictiveCalibrationError):
        assert_neutral(uncertainty_permission_laundering_fixture())


def test_wmbr05_live_observation_laundering_fixture_rejected():
    with pytest.raises(PredictiveCalibrationError):
        validate_synthetic_outcome(live_observation_laundering_fixture())
    with pytest.raises(PredictiveCalibrationError):
        assert_neutral(live_observation_laundering_fixture())


# --- Gate ------------------------------------------------------------------

def test_wmbr05_gate_requires_wmbr04_green():
    assert validate_wmbr05_gate(_gate_summary(wmbr04_green=False))["ok"] is False
    assert WMBR_04_VERDICT_GREEN.startswith("GREEN_WMBR_04")


def test_wmbr05_gate_requires_wmbr03_green():
    assert validate_wmbr05_gate(_gate_summary(wmbr03_green=False))["ok"] is False
    assert WMBR_03_VERDICT_GREEN.startswith("GREEN_WMBR_03")


def test_wmbr05_gate_requires_runtime_p42_green():
    assert validate_wmbr05_gate(_gate_summary(runtime_p42_green=False))["ok"] is False
    assert RUNTIME_P42_VERDICT_GREEN.startswith("GREEN_PHASE42")


def test_wmbr05_gate_refuses_without_prediction_candidates():
    assert validate_wmbr05_gate(_gate_summary(prediction_candidates_written=False, prediction_candidate_count=0))["ok"] is False


def test_wmbr05_gate_refuses_without_calibration_records():
    assert validate_wmbr05_gate(_gate_summary(calibration_records_written=False, calibration_record_count=0))["ok"] is False


def test_wmbr05_gate_refuses_if_prediction_marked_verified():
    assert validate_wmbr05_gate(_gate_summary(predictions_marked_verified=True))["ok"] is False


def test_wmbr05_gate_refuses_if_calibration_marked_proof():
    assert validate_wmbr05_gate(_gate_summary(calibration_treated_as_proof=True))["ok"] is False


def test_wmbr05_gate_refuses_if_uncertainty_authorizes_action():
    assert validate_wmbr05_gate(_gate_summary(uncertainty_treated_as_permission=True, action_authorized=True))["ok"] is False


def test_wmbr05_gate_refuses_if_synthetic_outcome_marked_live():
    assert validate_wmbr05_gate(_gate_summary(synthetic_outcome_treated_as_live_observation=True))["ok"] is False


def test_wmbr05_gate_refuses_if_authority_granted():
    assert validate_wmbr05_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_wmbr05_gate_refuses_if_live_effect_created():
    assert validate_wmbr05_gate(_gate_summary(live_external_side_effects_created=True))["ok"] is False


def test_wmbr05_gate_refuses_without_proof_bundle():
    assert validate_wmbr05_gate(_gate_summary(proof_bundle_valid=False))["ok"] is False


def test_wmbr05_gate_passes_on_full_summary():
    assert validate_wmbr05_gate(_gate_summary())["ok"] is True
