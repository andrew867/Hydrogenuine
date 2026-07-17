"""P29 tool workbench policy builder."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    P29_INVARIANTS,
    assert_neutral,
)


def build_tool_workbench_policy(*, policy_id: str = "p29-tool-workbench-policy-v1") -> dict:
    record = {
        "record_type": "tool_workbench_policy_v1",
        "schema_version": "1",
        "policy_id": policy_id,
        "provider_mode": PROVIDER_MODE,
        "live_tool_execution_enabled": False,
        "external_provider_enabled": False,
        "web_enabled": False,
        "filesystem_write_enabled": False,
        "patch_application_enabled": False,
        "delete_enabled": False,
        "tool_authorization_enabled": False,
        "automatic_belief_promotion_enabled": False,
        "operator_approval_required": True,
        "sandbox_only": True,
        "dry_run_only": True,
        "tool_plan_is_not_permission": True,
        "tool_request_is_not_execution": True,
        "sandbox_result_is_not_live_result": True,
        "dry_run_is_not_live_effect": True,
        "tool_receipt_is_not_authority": True,
        "domain_pack_does_not_grant_tools": True,
        "invariants": P29_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "tool_plan_treated_as_permission": False,
        "tool_request_executed_live": False,
        "sandbox_result_treated_as_live": False,
        "tool_authorization_granted": False,
        "tools_authorized": False,
        "authority_granted": False,
        "belief_promotion_automatic": False,
        "live_external_side_effects_created": False,
    }
    with_hash(record, "policy_hash")
    assert_neutral(record)
    return record
