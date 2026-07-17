"""Prediction candidates derived from causal hypotheses.

A prediction is not verification. Prediction candidates are provisional,
provenance-bound testable hypotheses — never truth and never authorization.
"""

from __future__ import annotations

from hg_runtime.predictive_calibration.schemas import (
    EMIT_PREDICTION_STATUSES,
    INSUFFICIENT_CONTEXT_STATUSES,
    PREDICTION_CANDIDATE_SCHEMA,
    PREDICTION_KINDS,
    PredictiveCalibrationError,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_prediction_candidate(
    *,
    hypothesis: dict,
    edge_ids: list[str],
    evidence_receipt_ids: list[str],
    kind_index: int = 0,
) -> dict | None:
    """Build a prediction candidate from a causal hypothesis.

    Returns None for RETRACTED sources (not emitted).
    PROPOSED hypotheses emit active candidates; others emit INSUFFICIENT_CONTEXT.
    """
    status = hypothesis.get("hypothesis_status", "INSUFFICIENT_EVIDENCE")
    if status == "RETRACTED":
        return None

    hyp_id = hypothesis["hypothesis_id"]
    if status in EMIT_PREDICTION_STATUSES:
        pred_status = "PROPOSED_UNTESTED"
        kind = PREDICTION_KINDS[kind_index % len(PREDICTION_KINDS)]
    elif status in INSUFFICIENT_CONTEXT_STATUSES:
        pred_status = "INSUFFICIENT_CONTEXT"
        kind = "QUALITATIVE"
    else:
        raise PredictiveCalibrationError(f"unsupported_hypothesis_status:{status}")

    text = f"[prediction-candidate from {hyp_id} kind={kind} status={pred_status}]"
    record = {
        "schema": PREDICTION_CANDIDATE_SCHEMA,
        "prediction_candidate_id": f"pcand-{hyp_id}",
        "source_hypothesis_id": hyp_id,
        "source_edge_ids": sorted(edge_ids),
        "source_evidence_receipt_ids": sorted(evidence_receipt_ids),
        "prediction_text_hash": canonical_hash({"text": text}),
        "prediction_text_redacted": text,
        "prediction_kind": kind,
        "prediction_status": pred_status,
        "prediction_is_verification": False,
        "truth_claimed": False,
        "action_authorized": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    record["candidate_hash"] = canonical_hash(record)
    return record


def validate_prediction_candidate(record: dict) -> None:
    """Refuse a prediction candidate that claims verification or truth."""
    if record.get("prediction_verified"):
        raise PredictiveCalibrationError("prediction_marked_verified")
    if record.get("prediction_is_verification") or record.get("prediction_treated_as_verification"):
        raise PredictiveCalibrationError("prediction_treated_as_verification")
    if record.get("truth_claimed"):
        raise PredictiveCalibrationError("truth_claimed")
    if record.get("action_authorized") or record.get("tools_authorized"):
        raise PredictiveCalibrationError("action_authorized")
