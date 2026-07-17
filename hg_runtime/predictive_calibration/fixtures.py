"""Deterministic WMBR-05 fixtures.

Fixtures exercise synthetic match/mismatch/partial/unknown calibration paths and
refuse prediction-verification, calibration-proof, uncertainty-permission, and
live-observation laundering.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.artifact_writer import build_causal_graph
from hg_runtime.causal_world_model_boundary.fixtures import fixture_ledger_bundle
from hg_runtime.predictive_calibration.calibration_score import build_calibration_record
from hg_runtime.predictive_calibration.prediction_candidate import build_prediction_candidate
from hg_runtime.predictive_calibration.schemas import OUTCOME_KINDS
from hg_runtime.predictive_calibration.synthetic_outcome import build_synthetic_outcome

FIXTURE_IDS = {
    "SYNTHETIC_MATCH": "SYNTHETIC_MATCH_FIXTURE",
    "SYNTHETIC_MISMATCH": "SYNTHETIC_MISMATCH_FIXTURE",
    "SYNTHETIC_PARTIAL": "SYNTHETIC_PARTIAL_FIXTURE",
    "SYNTHETIC_UNKNOWN": "SYNTHETIC_UNKNOWN_FIXTURE",
}


def fixture_causal_graph() -> dict:
    """Build an in-memory WMBR-04-shaped causal graph from fixtures."""
    graph = build_causal_graph(fixture_ledger_bundle())
    return {
        "source_bundle": "FIXTURE_WMBR04_CAUSAL_GRAPH",
        "hypotheses": graph["hypotheses"],
        "edges": graph["edges"],
        "predictions": graph["predictions"],
        "manifest": graph["manifest"],
        "summary": {"verdict": "GREEN_WMBR_04_CAUSAL_WORLD_MODEL_BOUNDARY"},
    }


def _proposed_hypothesis() -> dict:
    for hyp in fixture_causal_graph()["hypotheses"]:
        if hyp["hypothesis_status"] == "PROPOSED":
            return hyp
    raise RuntimeError("no_proposed_hypothesis_in_fixture")


def _contradicted_hypothesis() -> dict:
    for hyp in fixture_causal_graph()["hypotheses"]:
        if hyp["hypothesis_status"] == "CONTRADICTED":
            return hyp
    raise RuntimeError("no_contradicted_hypothesis_in_fixture")


def synthetic_match_fixture() -> dict:
    hyp = _proposed_hypothesis()
    cand = build_prediction_candidate(hypothesis=hyp, edge_ids=[], evidence_receipt_ids=[])
    assert cand is not None
    outcome = build_synthetic_outcome(
        prediction_candidate=cand,
        outcome_kind="SYNTHETIC_MATCH",
        fixture_id=FIXTURE_IDS["SYNTHETIC_MATCH"],
    )
    cal = build_calibration_record(prediction_candidate=cand, synthetic_outcome=outcome)
    return {"candidate": cand, "outcome": outcome, "calibration": cal}


def synthetic_mismatch_fixture() -> dict:
    hyp = _proposed_hypothesis()
    cand = build_prediction_candidate(hypothesis=hyp, edge_ids=[], evidence_receipt_ids=[])
    assert cand is not None
    outcome = build_synthetic_outcome(
        prediction_candidate=cand,
        outcome_kind="SYNTHETIC_MISMATCH",
        fixture_id=FIXTURE_IDS["SYNTHETIC_MISMATCH"],
    )
    cal = build_calibration_record(prediction_candidate=cand, synthetic_outcome=outcome)
    return {"candidate": cand, "outcome": outcome, "calibration": cal}


def synthetic_partial_fixture() -> dict:
    hyp = _proposed_hypothesis()
    cand = build_prediction_candidate(hypothesis=hyp, edge_ids=[], evidence_receipt_ids=[])
    assert cand is not None
    outcome = build_synthetic_outcome(
        prediction_candidate=cand,
        outcome_kind="SYNTHETIC_PARTIAL",
        fixture_id=FIXTURE_IDS["SYNTHETIC_PARTIAL"],
    )
    cal = build_calibration_record(prediction_candidate=cand, synthetic_outcome=outcome)
    return {"candidate": cand, "outcome": outcome, "calibration": cal}


def synthetic_unknown_fixture() -> dict:
    hyp = _proposed_hypothesis()
    cand = build_prediction_candidate(hypothesis=hyp, edge_ids=[], evidence_receipt_ids=[])
    assert cand is not None
    outcome = build_synthetic_outcome(
        prediction_candidate=cand,
        outcome_kind="SYNTHETIC_UNKNOWN",
        fixture_id=FIXTURE_IDS["SYNTHETIC_UNKNOWN"],
    )
    cal = build_calibration_record(prediction_candidate=cand, synthetic_outcome=outcome)
    return {"candidate": cand, "outcome": outcome, "calibration": cal}


def contradicted_hypothesis_fixture() -> dict:
    return {"hypothesis": _contradicted_hypothesis()}


def retracted_source_fixture() -> dict:
    return {
        "hypothesis": {
            "schema": "causal_hypothesis_record_v1",
            "hypothesis_id": "hyp-retracted-fixture",
            "hypothesis_status": "RETRACTED",
            "supporting_evidence_receipt_ids": [],
            "contradicting_evidence_receipt_ids": [],
        }
    }


def prediction_verification_laundering_fixture() -> dict:
    return {
        "schema": "prediction_candidate_v1",
        "prediction_candidate_id": "pcand-laundered-verified",
        "prediction_verified": True,
        "prediction_is_verification": True,
    }


def calibration_proof_laundering_fixture() -> dict:
    return {
        "schema": "calibration_record_v1",
        "calibration_id": "cal-laundered-proof",
        "calibration_is_proof": True,
        "truth_claimed": True,
    }


def uncertainty_permission_laundering_fixture() -> dict:
    return {
        "schema": "uncertainty_score_record_v1",
        "uncertainty_id": "unc-laundered-permission",
        "uncertainty_level": "LOW",
        "uncertainty_is_permission": True,
        "action_authorized": True,
    }


def live_observation_laundering_fixture() -> dict:
    return {
        "schema": "synthetic_outcome_receipt_v1",
        "synthetic_outcome_id": "sout-laundered-live",
        "live_observation": True,
        "synthetic_outcome_treated_as_live_observation": True,
    }


def outcome_cycle() -> list[str]:
    return list(OUTCOME_KINDS)
