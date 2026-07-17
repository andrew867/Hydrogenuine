"""Bounded mini-task definitions. Dry-run by default; live needs a permit."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.knowledge_acquisition.schemas import (
    MINI_TASK_SCHEMA,
    KnowledgeAcquisitionError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def define_mini_task(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("task_id", "domain", "objective", "scope", "mode"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    mode = data["mode"]
    if mode not in {"dry_run", "live"}:
        raise KnowledgeAcquisitionError("schema_violation:invalid_mode")
    if mode == "live" and not as_list(data, "permit_refs"):
        raise KnowledgeAcquisitionError("dry_live_boundary_enforced:live_requires_permit")

    data.setdefault("schema", MINI_TASK_SCHEMA)
    data.update(neutral_flags())
    return data


__all__ = ["define_mini_task"]
