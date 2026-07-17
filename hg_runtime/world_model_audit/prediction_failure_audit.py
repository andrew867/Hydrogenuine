"""Failed prediction audit records — failures remain visible."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    FAILED_PREDICTION_AUDIT_SCHEMA,
    FAILED_PREDICTION_REMAINS_VISIBLE,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_failed_prediction_audit(
    *,
    calibration_id: str,
    prediction_candidate_id: str,
    score_kind: str,
    failure_visible: bool = True,
) -> dict:
    record = {
        "schema": FAILED_PREDICTION_AUDIT_SCHEMA,
        "failed_prediction_audit_id": f"failed-prediction-audit-{calibration_id}",
        "calibration_id": calibration_id,
        "prediction_candidate_id": prediction_candidate_id,
        "score_kind": score_kind,
        "failed_prediction_remains_visible": failure_visible,
        "doctrine": FAILED_PREDICTION_REMAINS_VISIBLE,
        "prediction_treated_as_verification": False,
        "calibration_treated_as_proof": False,
        "deletion_performed": False,
        "rewrite_performed": False,
        "audit_closure_treated_as_laundering": False,
        **neutral_flags(),
    }
    record["audit_hash"] = canonical_hash(record)
    assert_neutral(record)
    return record


def validate_failed_prediction_audit(record: dict) -> None:
    if record.get("schema") != FAILED_PREDICTION_AUDIT_SCHEMA:
        raise ValueError("invalid_failed_prediction_audit_schema")
    if not record.get("failed_prediction_remains_visible"):
        raise ValueError("failed_prediction_must_remain_visible")
    assert_neutral(record)
