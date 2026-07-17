"""P31 competence claim refusal — records when overbroad claims are refused."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import (
    COMPETENCE_CLAIM_TYPES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
)


def create_competence_claim_refusal(
    *,
    model_id: str,
    claim_type: str,
    claim_text: str = "",
    reason: str = "",
) -> dict[str, Any]:
    if claim_type not in COMPETENCE_CLAIM_TYPES:
        raise EvaluationHarnessBoundaryError(f"unknown_claim_type:{claim_type}")
    record = {
        "schema": "competence_claim_refusal_v1",
        "model_id": model_id,
        "claim_type": claim_type,
        "claim_text": claim_text[:500],
        "refused": True,
        "reason": reason or f"refused:{claim_type}",
        "competence_claimed": False,
        "evaluation_treated_as_truth": False,
    }
    assert_neutral(record)
    return with_hash(record, "refusal_hash")


def refuse_if_competence_claim(record: dict[str, Any]) -> dict[str, Any] | None:
    for claim_type in COMPETENCE_CLAIM_TYPES:
        key = claim_type.replace("_treated_as_", "_is_").replace("_requested", "_granted")
        if record.get(claim_type) or record.get(key):
            return create_competence_claim_refusal(
                model_id=record.get("model_id", "unknown"),
                claim_type=claim_type,
                reason=f"refused_automatically:{claim_type}",
            )
    return None
