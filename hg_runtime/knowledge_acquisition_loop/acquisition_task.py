"""P30 acquisition task builder."""

from __future__ import annotations

from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.schemas import (
    ACQUISITION_TASK_TYPES,
    KnowledgeAcquisitionBoundaryError,
    assert_neutral,
    neutral_flags,
)


def build_acquisition_task(
    *,
    task_id: str,
    task_type: str,
    candidate_id: str,
    description: str,
    source_refs: list[str] | None = None,
    fixture_only: bool = True,
    sandbox_only: bool = True,
) -> dict:
    if task_type not in ACQUISITION_TASK_TYPES:
        raise KnowledgeAcquisitionBoundaryError(f"unknown_task_type:{task_type}")
    record = {
        "record_type": "acquisition_task_v1",
        "schema_version": "1",
        "task_id": task_id,
        "task_type": task_type,
        "candidate_id": candidate_id,
        "description": description,
        "source_refs": list(source_refs or []),
        "fixture_only": fixture_only,
        "sandbox_only": sandbox_only,
        "acquisition_task_is_not_action": True,
        "doctrine_note": "Acquisition task is not action.",
        **neutral_flags(),
    }
    with_hash(record, "task_hash")
    assert_neutral(record)
    return record
