"""Contradiction audit records — contradictions remain visible."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    CONTRADICTION_AUDIT_SCHEMA,
    CONTRADICTION_REMAINS_VISIBLE,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_contradiction_audit(
    *,
    hypothesis_id: str,
    prediction_candidate_id: str | None,
    drift_id: str | None,
    contradiction_visible: bool = True,
) -> dict:
    record = {
        "schema": CONTRADICTION_AUDIT_SCHEMA,
        "contradiction_audit_id": f"contradiction-audit-{hypothesis_id}",
        "hypothesis_id": hypothesis_id,
        "prediction_candidate_id": prediction_candidate_id,
        "drift_id": drift_id,
        "contradiction_remains_visible": contradiction_visible,
        "doctrine": CONTRADICTION_REMAINS_VISIBLE,
        "deletion_performed": False,
        "rewrite_performed": False,
        "audit_closure_treated_as_laundering": False,
        **neutral_flags(),
    }
    record["audit_hash"] = canonical_hash(record)
    assert_neutral(record)
    return record


def validate_contradiction_audit(record: dict) -> None:
    if record.get("schema") != CONTRADICTION_AUDIT_SCHEMA:
        raise ValueError("invalid_contradiction_audit_schema")
    if not record.get("contradiction_remains_visible"):
        raise ValueError("contradiction_must_remain_visible")
    assert_neutral(record)
