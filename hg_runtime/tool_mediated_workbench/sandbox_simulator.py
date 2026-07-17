"""P29-2 sandbox simulator — dry-run fixture tool plans."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.tool_refusal import build_refusal_record
from hg_runtime.tool_mediated_workbench.tool_sandbox import build_sandbox_result

_REFUSED_REQUEST_TYPES = {
    "web_fetch": "live_web_request",
    "external_provider_call": "external_provider_request",
    "local_write": "filesystem_write_request",
    "patch_application": "patch_application_request",
    "deletion": "deletion_request",
    "authority_grant": "authority_grant_request",
}


def simulate_tool_plan(*, plan: dict, requests: list[dict], policy: dict) -> dict:
    sandbox_results = []
    refusals = []

    for req in requests:
        req_type = req["request_type"]
        refusal_reason = _REFUSED_REQUEST_TYPES.get(req_type)

        if refusal_reason:
            sandbox = build_sandbox_result(
                sandbox_id=f"sandbox-{req['request_id']}",
                request_id=req["request_id"],
                plan_id=plan["plan_id"],
                result_state="REFUSED_BY_POLICY",
                refusal_reason=refusal_reason,
            )
            refusal = build_refusal_record(
                refusal_id=f"refusal-{req['request_id']}",
                request_id=req["request_id"],
                plan_id=plan["plan_id"],
                refusal_reason=refusal_reason,
                detail=f"Request type {req_type} refused by workbench policy",
            )
            sandbox_results.append(sandbox)
            refusals.append(refusal)
        elif not req.get("requires_operator_approval", True):
            sandbox = build_sandbox_result(
                sandbox_id=f"sandbox-{req['request_id']}",
                request_id=req["request_id"],
                plan_id=plan["plan_id"],
                result_state="REFUSED_MISSING_APPROVAL",
                refusal_reason="operator_approval_missing",
            )
            refusal = build_refusal_record(
                refusal_id=f"refusal-{req['request_id']}",
                request_id=req["request_id"],
                plan_id=plan["plan_id"],
                refusal_reason="operator_approval_missing",
                detail="Operator approval not granted",
            )
            sandbox_results.append(sandbox)
            refusals.append(refusal)
        else:
            sandbox = build_sandbox_result(
                sandbox_id=f"sandbox-{req['request_id']}",
                request_id=req["request_id"],
                plan_id=plan["plan_id"],
                result_state="DRY_RUN_COMPLETE",
                simulated_output=f"dry_run_output_for_{req['tool_name']}",
            )
            sandbox_results.append(sandbox)

    if plan.get("domain_pack_does_not_grant_tools") is not True:
        refusals.append(build_refusal_record(
            refusal_id=f"refusal-pack-{plan['plan_id']}",
            request_id=plan["tool_request_ids"][0] if plan.get("tool_request_ids") else "unknown",
            plan_id=plan["plan_id"],
            refusal_reason="domain_pack_claims_tool_permission",
            detail="Domain pack attempted to claim tool permission",
        ))

    return {
        "plan_id": plan["plan_id"],
        "sandbox_results": sandbox_results,
        "refusals": refusals,
    }
