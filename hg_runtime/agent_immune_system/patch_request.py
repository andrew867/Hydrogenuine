"""AIS-7 patch-candidate request records."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import assert_neutral, neutral_flags


def build_patch_candidate_request(
    *,
    request_id: str,
    source_finding_id: str,
    finding_type: str,
    requested_scope: str,
) -> dict:
    request = {
        "schema_version": "1",
        "record_type": "patch_hygiene_task_v1",
        "request_id": request_id,
        "source_finding_id": source_finding_id,
        "finding_type": finding_type,
        "requested_scope": requested_scope,
        "request_type": "PATCH_CANDIDATE_REQUEST",
        "patch_candidate_request_is_not_patch": True,
        "repair_recommendation_is_not_patch_permission": True,
        "operator_approval_required": True,
        "dry_run_apply_required_later": True,
        "rollback_plan_required": True,
        "patch_applied": False,
        "live_mutation_performed": False,
        "candidate_deployed": False,
        **neutral_flags(),
    }
    request["record_hash"] = record_hash(request)
    assert_neutral(request)
    return request
