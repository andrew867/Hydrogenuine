"""Deterministic WMBR-06 fixtures."""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.fixtures import fixture_ledger_bundle
from hg_runtime.predictive_calibration.fixtures import (
    contradicted_hypothesis_fixture,
    fixture_causal_graph,
    retracted_source_fixture,
    synthetic_mismatch_fixture,
)
from hg_runtime.predictive_calibration.artifact_writer import build_calibration_layer
from hg_runtime.world_model_audit.schemas import assert_neutral


def fixture_calibration_bundle() -> dict:
    """Build an in-memory WMBR-05-shaped bundle from fixtures."""
    graph = fixture_causal_graph()
    out = build_calibration_layer(graph)
    return {
        "source_bundle": "FIXTURE_WMBR05_CALIBRATION",
        "prediction_candidates": out["prediction_candidates"],
        "synthetic_outcomes": out["synthetic_outcomes"],
        "calibration_records": out["calibration_records"],
        "uncertainty_scores": out["uncertainty_scores"],
        "drift_records": out["drift_records"],
        "hypotheses": out["hypotheses"],
        "edges": out["edges"],
        "manifest": out["manifest"],
        "summary": {"verdict": "GREEN_WMBR_05_PREDICTIVE_CALIBRATION_UNCERTAINTY"},
        "retraction_records": fixture_ledger_bundle()["retraction_records"],
    }


def stale_prediction_fixture() -> dict:
    bundle = fixture_calibration_bundle()
    for cand in bundle["prediction_candidates"]:
        if cand.get("prediction_status") == "INSUFFICIENT_CONTEXT":
            return {"candidate": cand}
    cand = bundle["prediction_candidates"][0].copy()
    cand["prediction_status"] = "INSUFFICIENT_CONTEXT"
    return {"candidate": cand}


def failed_prediction_fixture() -> dict:
    return synthetic_mismatch_fixture()


def contradicted_hypothesis_fixture_wmbr06() -> dict:
    return contradicted_hypothesis_fixture()


def retracted_belief_source_fixture() -> dict:
    return retracted_source_fixture()


def unsupported_belief_state_fixture() -> dict:
    return {
        "belief_state": {
            "schema": "belief_state_record_v1",
            "belief_state_id": "belief-unsupported-fixture",
            "belief_status": "UNVERIFIED",
            "truth_claimed": False,
        }
    }


def low_confidence_hypothesis_fixture() -> dict:
    bundle = fixture_calibration_bundle()
    for unc in bundle["uncertainty_scores"]:
        if unc.get("uncertainty_level") in ("HIGH", "UNKNOWN"):
            return {"uncertainty": unc}
    return {"uncertainty": bundle["uncertainty_scores"][0]}


def audit_laundering_attempt_fixture() -> dict:
    return {
        "schema": "world_model_record_audit_v1",
        "audit_id": "audit-laundered-green",
        "audit_closure_treated_as_laundering": True,
        "failed_predictions_hidden": True,
        "truth_claimed": True,
    }


def deletion_rewrite_attempt_fixture() -> dict:
    return {
        "schema": "decay_record_v1",
        "decay_id": "decay-delete-attempt",
        "deletion_performed": True,
        "rewrite_performed": True,
        "decay_treated_as_deletion": True,
    }


def action_authorization_attempt_fixture() -> dict:
    return {
        "schema": "maintenance_policy_receipt_v1",
        "policy_id": "policy-auth-attempt",
        "action_authorized": True,
        "tools_authorized": True,
        "authority_granted": True,
    }


def truth_certainty_laundering_attempt_fixture() -> dict:
    return {
        "schema": "contradiction_audit_record_v1",
        "contradiction_audit_id": "truth-launder",
        "truth_claimed": True,
        "certainty_claimed": True,
        "belief_state_treated_as_truth": True,
    }
