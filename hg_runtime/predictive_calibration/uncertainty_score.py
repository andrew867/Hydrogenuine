"""Uncertainty score records.

An uncertainty score is not permission. A confidence score is not authority.
Scores are bounded metadata derived from hypothesis status and calibration.
"""

from __future__ import annotations

from hg_runtime.predictive_calibration.schemas import (
    UNCERTAINTY_SCORE_SCHEMA,
    PredictiveCalibrationError,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

_BASE_UNCERTAINTY = {
    "PROPOSED": ("MEDIUM", 0.55, ["provisional_hypothesis"]),
    "CONTRADICTED": ("HIGH", 0.85, ["contradicted_hypothesis"]),
    "INSUFFICIENT_EVIDENCE": ("HIGH", 0.80, ["insufficient_evidence"]),
    "RETRACTED": ("UNKNOWN", 0.95, ["retracted_source"]),
    "NEEDS_TEST": ("HIGH", 0.75, ["needs_test"]),
}

_CALIBRATION_ADJUSTMENTS = {
    "EXACT_MATCH": (0.0, []),  # success remains provisional — no authority bump
    "PARTIAL_MATCH": (0.05, ["partial_synthetic_match"]),
    "MISMATCH": (0.15, ["synthetic_mismatch"]),
    "UNKNOWN": (0.10, ["synthetic_unknown"]),
}


def build_uncertainty_score(
    *,
    prediction_candidate: dict,
    hypothesis: dict,
    calibration_record: dict | None = None,
) -> dict:
    hyp_status = hypothesis.get("hypothesis_status", "INSUFFICIENT_EVIDENCE")
    base_level, base_confidence, reasons = _BASE_UNCERTAINTY.get(
        hyp_status, ("UNKNOWN", 0.90, ["unknown_hypothesis_status"])
    )
    reasons = list(reasons)
    confidence = base_confidence

    if calibration_record:
        adj, adj_reasons = _CALIBRATION_ADJUSTMENTS.get(
            calibration_record["score_kind"], (0.0, [])
        )
        confidence = min(0.99, confidence + adj)
        reasons.extend(adj_reasons)

    if prediction_candidate.get("prediction_status") == "INSUFFICIENT_CONTEXT":
        base_level = "HIGH" if base_level != "UNKNOWN" else "UNKNOWN"
        reasons.append("insufficient_context")

    pcand_id = prediction_candidate["prediction_candidate_id"]
    record = {
        "schema": UNCERTAINTY_SCORE_SCHEMA,
        "uncertainty_id": f"unc-{pcand_id}",
        "prediction_candidate_id": pcand_id,
        "source_hypothesis_id": hypothesis["hypothesis_id"],
        "uncertainty_level": base_level,
        "uncertainty_reasons": sorted(set(reasons)),
        "confidence_score": round(confidence, 4),
        "confidence_is_authority": False,
        "uncertainty_is_permission": False,
        "action_authorized": False,
        **neutral_flags(),
    }
    record["uncertainty_hash"] = canonical_hash(record)
    return record


def validate_uncertainty_score(record: dict) -> None:
    if record.get("uncertainty_is_permission") or record.get("action_authorized"):
        raise PredictiveCalibrationError("uncertainty_treated_as_permission")
    if record.get("confidence_is_authority"):
        raise PredictiveCalibrationError("confidence_treated_as_authority")
