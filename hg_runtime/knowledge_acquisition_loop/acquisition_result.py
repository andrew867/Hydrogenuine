"""P30 acquisition result builder."""

from __future__ import annotations

from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.schemas import (
    ACQUISITION_RESULT_STATES,
    KnowledgeAcquisitionBoundaryError,
    assert_neutral,
    neutral_flags,
)


def build_acquisition_result(
    *,
    result_id: str,
    task_id: str,
    result_state: str,
    source_id: str | None = None,
    acquired_content: str | None = None,
    refusal_reason: str | None = None,
) -> dict:
    if result_state not in ACQUISITION_RESULT_STATES:
        raise KnowledgeAcquisitionBoundaryError(f"unknown_result_state:{result_state}")
    record = {
        "record_type": "acquisition_result_v1",
        "schema_version": "1",
        "result_id": result_id,
        "task_id": task_id,
        "result_state": result_state,
        "source_id": source_id,
        "acquired_content": acquired_content,
        "refusal_reason": refusal_reason,
        "acquisition_result_is_not_belief": True,
        "acquired_claim_is_not_truth": True,
        "doctrine_note": "Acquisition result is not belief. Acquired claim is not truth.",
        **neutral_flags(),
    }
    with_hash(record, "result_hash")
    assert_neutral(record)
    return record
