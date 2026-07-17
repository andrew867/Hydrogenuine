"""P29-2 tool refusal record builder."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import (
    REFUSAL_REASONS,
    ToolWorkbenchBoundaryError,
    assert_neutral,
    neutral_flags,
)


def build_refusal_record(
    *,
    refusal_id: str,
    request_id: str,
    plan_id: str,
    refusal_reason: str,
    detail: str | None = None,
) -> dict:
    if refusal_reason not in REFUSAL_REASONS:
        raise ToolWorkbenchBoundaryError(f"unknown_refusal_reason:{refusal_reason}")
    record = {
        "record_type": "tool_refusal_record_v1",
        "schema_version": "1",
        "refusal_id": refusal_id,
        "request_id": request_id,
        "plan_id": plan_id,
        "refusal_reason": refusal_reason,
        "detail": detail,
        "action_performed": False,
        "status": "REFUSED",
        "doctrine_note": "Tool request refused by policy.",
        **neutral_flags(),
    }
    with_hash(record, "refusal_hash")
    assert_neutral(record)
    return record
