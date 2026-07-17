"""Deterministic synthetic outcome receipts.

A synthetic outcome is not a live observation. These receipts exist solely to
exercise calibration mechanics in fixture-only mode.
"""

from __future__ import annotations

from hg_runtime.predictive_calibration.schemas import (
    OUTCOME_KINDS,
    SYNTHETIC_OUTCOME_SCHEMA,
    PredictiveCalibrationError,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_synthetic_outcome(
    *,
    prediction_candidate: dict,
    outcome_kind: str,
    fixture_id: str,
) -> dict:
    if outcome_kind not in OUTCOME_KINDS:
        raise PredictiveCalibrationError(f"invalid_outcome_kind:{outcome_kind}")

    pcand_id = prediction_candidate["prediction_candidate_id"]
    text = f"[synthetic-outcome {outcome_kind} for {pcand_id} fixture={fixture_id}]"
    record = {
        "schema": SYNTHETIC_OUTCOME_SCHEMA,
        "synthetic_outcome_id": f"sout-{pcand_id}-{fixture_id}",
        "prediction_candidate_id": pcand_id,
        "outcome_kind": outcome_kind,
        "outcome_text_hash": canonical_hash({"text": text}),
        "outcome_text_redacted": text,
        "live_observation": False,
        "external_call_made": False,
        "fixture_id": fixture_id,
        **neutral_flags(),
    }
    record["outcome_hash"] = canonical_hash(record)
    return record


def validate_synthetic_outcome(record: dict) -> None:
    if record.get("live_observation") or record.get("synthetic_outcome_treated_as_live_observation"):
        raise PredictiveCalibrationError("synthetic_outcome_treated_as_live")
    if record.get("external_call_made"):
        raise PredictiveCalibrationError("external_provider_call")
