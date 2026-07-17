"""P29 tool plan builder."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import assert_neutral, neutral_flags


def build_tool_plan(
    *,
    plan_id: str,
    domain_pack_id: str,
    skill_ids: list[str],
    tool_requests: list[dict],
    provenance_refs: list[str],
    capability_gaps: list[str] | None = None,
    requires_operator_approval: bool = True,
) -> dict:
    record = {
        "record_type": "tool_plan_v1",
        "schema_version": "1",
        "plan_id": plan_id,
        "domain_pack_id": domain_pack_id,
        "skill_ids": list(skill_ids),
        "tool_request_ids": [r["request_id"] for r in tool_requests],
        "tool_request_count": len(tool_requests),
        "provenance_refs": list(provenance_refs),
        "capability_gaps": list(capability_gaps or []),
        "requires_operator_approval": requires_operator_approval,
        "tool_plan_is_not_permission": True,
        "domain_pack_does_not_grant_tools": True,
        "doctrine_note": "Tool plan is not permission. Domain pack does not grant tools.",
        **neutral_flags(),
    }
    with_hash(record, "plan_hash")
    assert_neutral(record)
    return record
