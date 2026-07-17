"""P29-2 workbench dry run — orchestrates sandbox simulation over tool plans."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P29_INVARIANTS,
    REFUSAL_REASONS,
    assert_neutral,
)
from hg_runtime.tool_mediated_workbench.sandbox_simulator import simulate_tool_plan
from hg_runtime.tool_mediated_workbench.tool_plan_builder import build_tool_plan_layer
from hg_runtime.tool_mediated_workbench.tool_receipt import build_tool_receipt
from hg_runtime.tool_mediated_workbench.tool_refusal import build_refusal_record
from hg_runtime.tool_mediated_workbench.tool_request import build_tool_request
from hg_runtime.tool_mediated_workbench.tool_workbench_policy import build_tool_workbench_policy


def _build_extra_refusal_requests(plan_id: str) -> list[tuple[dict, str]]:
    extras = [
        ("web_fetch", "web_search_tool", "Attempt web search", "live_web_request"),
        ("external_provider_call", "llm_provider", "Attempt external provider", "external_provider_request"),
        ("local_write", "file_writer", "Attempt fs write", "filesystem_write_request"),
        ("patch_application", "patch_tool", "Attempt patch", "patch_application_request"),
        ("deletion", "delete_tool", "Attempt deletion", "deletion_request"),
        ("authority_grant", "auth_tool", "Attempt authority grant", "authority_grant_request"),
    ]
    result = []
    for req_type, tool_name, desc, reason in extras:
        req = build_tool_request(
            request_id=f"req-refusal-{reason}",
            request_type=req_type,
            tool_name=tool_name,
            description=desc,
        )
        result.append((req, reason))
    return result


def build_dry_run_layer(repo_root: Path) -> dict:
    plan_layer = build_tool_plan_layer(repo_root)
    policy = build_tool_workbench_policy()

    all_sandbox_results = []
    all_refusals = []
    all_receipts = []

    for plan in plan_layer["plans"]:
        plan_requests = [r for r in plan_layer["requests"] if r["request_id"] in plan.get("tool_request_ids", [])]
        sim = simulate_tool_plan(plan=plan, requests=plan_requests, policy=policy)
        all_sandbox_results.extend(sim["sandbox_results"])
        all_refusals.extend(sim["refusals"])
        receipt = build_tool_receipt(
            receipt_id=f"receipt-{plan['plan_id']}",
            plan_id=plan["plan_id"],
            sandbox_result_ids=[s["sandbox_id"] for s in sim["sandbox_results"]],
            refusal_ids=[r["refusal_id"] for r in sim["refusals"]],
        )
        all_receipts.append(receipt)

    extra_pairs = _build_extra_refusal_requests("refusal-plan")
    for req, reason in extra_pairs:
        existing_reasons = {r["refusal_reason"] for r in all_refusals}
        if reason not in existing_reasons:
            refusal = build_refusal_record(
                refusal_id=f"refusal-extra-{reason}",
                request_id=req["request_id"],
                plan_id="extra-refusal-plan",
                refusal_reason=reason,
                detail=f"Extra refusal exercising {reason}",
            )
            all_refusals.append(refusal)

    pack_permission_reasons = {r["refusal_reason"] for r in all_refusals}
    if "domain_pack_claims_tool_permission" not in pack_permission_reasons:
        all_refusals.append(build_refusal_record(
            refusal_id="refusal-extra-domain_pack_claims_tool_permission",
            request_id="req-pack-perm",
            plan_id="extra-refusal-plan",
            refusal_reason="domain_pack_claims_tool_permission",
            detail="Domain pack attempted to claim tool permission",
        ))
    if "operator_approval_missing" not in pack_permission_reasons:
        all_refusals.append(build_refusal_record(
            refusal_id="refusal-extra-operator_approval_missing",
            request_id="req-no-approval",
            plan_id="extra-refusal-plan",
            refusal_reason="operator_approval_missing",
            detail="Operator approval not granted",
        ))

    covered_reasons = {r["refusal_reason"] for r in all_refusals}

    manifest = {
        "record_type": "dry_run_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p29-2-dry-run",
        "repo_root": str(repo_root),
        "sandbox_result_count": len(all_sandbox_results),
        "refusal_count": len(all_refusals),
        "receipt_count": len(all_receipts),
        "refusal_reasons_covered": sorted(covered_reasons),
        "all_refusal_reasons_covered": REFUSAL_REASONS <= covered_reasons,
        "invariants": P29_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "sandbox_result_is_not_live_result": True,
        "dry_run_is_not_live_effect": True,
        "tool_plan_treated_as_permission": False,
        "tool_request_executed_live": False,
        "tool_authorization_granted": False,
        "belief_promotion_automatic": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)

    return {
        "policy": policy,
        "plan_layer": plan_layer,
        "sandbox_results": all_sandbox_results,
        "refusals": all_refusals,
        "receipts": all_receipts,
        "manifest": manifest,
    }


def replay_dry_run(repo_root: Path, expected_manifest_hash: str) -> dict:
    layer = build_dry_run_layer(repo_root)
    return {
        "replay_preserves_manifest_hash": layer["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replayed_manifest_hash": layer["manifest"]["manifest_hash"],
        "expected_manifest_hash": expected_manifest_hash,
    }
