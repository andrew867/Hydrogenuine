"""Stale record detection — marks remain visible."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    STALE_MARKER_SCHEMA,
    STALE_REASONS,
    STALE_RECORD_REMAINS_VISIBLE,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def detect_stale_prediction(candidate: dict, hypothesis: dict | None = None) -> dict | None:
    """Return a stale marker when a prediction candidate is stale but visible."""
    status = candidate.get("prediction_status", "")
    reason: str | None = None

    if status == "INSUFFICIENT_CONTEXT":
        reason = "INSUFFICIENT_CONTEXT"
    elif hypothesis and hypothesis.get("hypothesis_status") == "CONTRADICTED":
        reason = "CONTRADICTED_HYPOTHESIS"
    elif hypothesis and hypothesis.get("hypothesis_status") == "RETRACTED":
        reason = "RETRACTED_SOURCE"

    if reason is None:
        return None

    marker = {
        "schema": STALE_MARKER_SCHEMA,
        "marker_id": f"stale-{candidate['prediction_candidate_id']}",
        "target_record_id": candidate["prediction_candidate_id"],
        "target_record_kind": "prediction_candidate",
        "stale_reason": reason,
        "stale_record_remains_visible": True,
        "doctrine": STALE_RECORD_REMAINS_VISIBLE,
        "deletion_performed": False,
        "rewrite_performed": False,
        **neutral_flags(),
    }
    marker["marker_hash"] = canonical_hash(marker)
    assert_neutral(marker)
    return marker


def detect_stale_uncertainty(uncertainty: dict) -> dict | None:
    """Mark high-uncertainty scores as stale for review (low confidence in claim)."""
    if uncertainty.get("uncertainty_level") not in ("HIGH", "UNKNOWN"):
        return None

    marker = {
        "schema": STALE_MARKER_SCHEMA,
        "marker_id": f"stale-{uncertainty['uncertainty_id']}",
        "target_record_id": uncertainty["uncertainty_id"],
        "target_record_kind": "uncertainty_score",
        "stale_reason": "LOW_CONFIDENCE",
        "stale_record_remains_visible": True,
        "doctrine": STALE_RECORD_REMAINS_VISIBLE,
        "deletion_performed": False,
        "rewrite_performed": False,
        **neutral_flags(),
    }
    marker["marker_hash"] = canonical_hash(marker)
    assert_neutral(marker)
    return marker


def validate_stale_marker(marker: dict) -> None:
    if marker.get("schema") != STALE_MARKER_SCHEMA:
        raise ValueError("invalid_stale_marker_schema")
    if marker.get("stale_reason") not in STALE_REASONS:
        raise ValueError("invalid_stale_reason")
    if not marker.get("stale_record_remains_visible"):
        raise ValueError("stale_record_must_remain_visible")
    assert_neutral(marker)
