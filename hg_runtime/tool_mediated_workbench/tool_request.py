"""P29 tool request builder."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import (
    TOOL_REQUEST_TYPES,
    ToolWorkbenchBoundaryError,
    assert_neutral,
    neutral_flags,
)


def build_tool_request(
    *,
    request_id: str,
    request_type: str,
    tool_name: str,
    description: str,
    domain_pack_id: str | None = None,
    skill_id: str | None = None,
    provenance_refs: list[str] | None = None,
    requires_operator_approval: bool = True,
) -> dict:
    if request_type not in TOOL_REQUEST_TYPES:
        raise ToolWorkbenchBoundaryError(f"unknown_request_type:{request_type}")
    record = {
        "record_type": "tool_request_v1",
        "schema_version": "1",
        "request_id": request_id,
        "request_type": request_type,
        "tool_name": tool_name,
        "description": description,
        "domain_pack_id": domain_pack_id,
        "skill_id": skill_id,
        "provenance_refs": list(provenance_refs or []),
        "requires_operator_approval": requires_operator_approval,
        "tool_request_is_not_execution": True,
        "doctrine_note": "Tool request is not execution.",
        **neutral_flags(),
    }
    with_hash(record, "request_hash")
    assert_neutral(record)
    return record
