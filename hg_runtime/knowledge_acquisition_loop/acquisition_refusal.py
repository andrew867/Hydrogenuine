"""P30 acquisition refusal builder."""

from __future__ import annotations

from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.schemas import (
    REFUSAL_REASONS,
    KnowledgeAcquisitionBoundaryError,
    assert_neutral,
    neutral_flags,
)


def build_acquisition_refusal(
    *,
    refusal_id: str,
    task_id: str,
    refusal_reason: str,
    description: str,
) -> dict:
    if refusal_reason not in REFUSAL_REASONS:
        raise KnowledgeAcquisitionBoundaryError(f"unknown_refusal_reason:{refusal_reason}")
    record = {
        "record_type": "acquisition_refusal_v1",
        "schema_version": "1",
        "refusal_id": refusal_id,
        "task_id": task_id,
        "refusal_reason": refusal_reason,
        "description": description,
        "acquired_claim_is_not_truth": True,
        "acquisition_result_is_not_belief": True,
        "doctrine_note": "Refusal preserves safety boundary.",
        **neutral_flags(),
    }
    with_hash(record, "refusal_hash")
    assert_neutral(record)
    return record
