"""Prediction drift detection.

Drift records keep mismatches and contradictions visible. Truth is never resolved
by drift detection — revision may be required but verification is not claimed.
"""

from __future__ import annotations

from hg_runtime.predictive_calibration.schemas import (
    DRIFT_TYPES,
    PREDICTION_DRIFT_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_drift_record(
    *,
    prediction_candidate: dict,
    hypothesis: dict,
    drift_type: str,
    revision_required: bool = True,
) -> dict:
    if drift_type not in DRIFT_TYPES:
        raise ValueError(f"invalid_drift_type:{drift_type}")

    pcand_id = prediction_candidate["prediction_candidate_id"]
    record = {
        "schema": PREDICTION_DRIFT_SCHEMA,
        "drift_id": f"drift-{pcand_id}-{drift_type.lower()}",
        "prediction_candidate_id": pcand_id,
        "source_hypothesis_id": hypothesis["hypothesis_id"],
        "drift_type": drift_type,
        "drift_visible": True,
        "truth_resolved": False,
        "revision_required": revision_required,
        **neutral_flags(),
    }
    record["drift_hash"] = canonical_hash(record)
    return record


def detect_drift(
    *,
    prediction_candidate: dict,
    hypothesis: dict,
    calibration_record: dict | None,
) -> dict | None:
    """Return a drift record when performance mismatch or source conflict is visible."""
    hyp_status = hypothesis.get("hypothesis_status")
    if hyp_status == "CONTRADICTED":
        return build_drift_record(
            prediction_candidate=prediction_candidate,
            hypothesis=hypothesis,
            drift_type="CONTRADICTED_HYPOTHESIS",
        )
    if prediction_candidate.get("prediction_status") == "INSUFFICIENT_CONTEXT":
        return build_drift_record(
            prediction_candidate=prediction_candidate,
            hypothesis=hypothesis,
            drift_type="INSUFFICIENT_CONTEXT",
        )
    if calibration_record and calibration_record.get("score_kind") == "MISMATCH":
        return build_drift_record(
            prediction_candidate=prediction_candidate,
            hypothesis=hypothesis,
            drift_type="SYNTHETIC_MISMATCH",
        )
    return None
