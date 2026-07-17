"""Calibration records.

A calibration record is not proof. It scores fixture-only synthetic outcomes
against prediction candidates without claiming truth or granting authority.
"""

from __future__ import annotations

from hg_runtime.predictive_calibration.schemas import (
    CALIBRATION_RECORD_SCHEMA,
    PredictiveCalibrationError,
    neutral_flags,
)
from hg_runtime.predictive_calibration.scoring_policy import score_kind_for_outcome
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_calibration_record(
    *,
    prediction_candidate: dict,
    synthetic_outcome: dict,
) -> dict:
    score_kind, score_value, interpretation = score_kind_for_outcome(
        synthetic_outcome["outcome_kind"]
    )
    pcand_id = prediction_candidate["prediction_candidate_id"]
    sout_id = synthetic_outcome["synthetic_outcome_id"]
    record = {
        "schema": CALIBRATION_RECORD_SCHEMA,
        "calibration_id": f"cal-{pcand_id}-{synthetic_outcome['fixture_id']}",
        "prediction_candidate_id": pcand_id,
        "synthetic_outcome_id": sout_id,
        "score_kind": score_kind,
        "score_value": score_value,
        "score_interpretation": interpretation,
        "calibration_is_proof": False,
        "truth_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    record["calibration_hash"] = canonical_hash(record)
    return record


def validate_calibration_record(record: dict) -> None:
    if record.get("calibration_is_proof") or record.get("calibration_treated_as_proof"):
        raise PredictiveCalibrationError("calibration_treated_as_proof")
    if record.get("truth_claimed") or record.get("authority_granted"):
        raise PredictiveCalibrationError("calibration_treated_as_proof")
