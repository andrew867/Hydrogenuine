"""AIS-7 rollback plan records."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import assert_neutral, neutral_flags


def build_rollback_plan(*, rollback_plan_id: str, request_id: str) -> dict:
    plan = {
        "schema_version": "1",
        "record_type": "rollback_plan_v1",
        "rollback_plan_id": rollback_plan_id,
        "request_id": request_id,
        "rollback_required_before_apply": True,
        "rollback_plan_is_not_apply_permission": True,
        "dry_run_first": True,
        "operator_approval_required": True,
        "rollback_executed": False,
        "patch_applied": False,
        **neutral_flags(),
    }
    plan["record_hash"] = record_hash(plan)
    assert_neutral(plan)
    return plan
