"""AIS-7 patch hygiene planner gate validation."""

from __future__ import annotations

from typing import Any, Mapping

VERDICT_GREEN = "GREEN_AIS_7_PATCH_HYGIENE_PLANNER"
VERDICT_RED = "RED_AIS_7_PATCH_HYGIENE_PLANNER_FAILED"
PHASE_ID = "AIS-7"
GATE_RESULT_SCHEMA = "ais_7_gate_result_v1"


def validate_ais7_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "ais6_green": "ais6_not_green",
        "patch_candidate_requests_written": "requests_required",
        "rollback_plans_written": "rollback_plans_required",
        "vulnerability_finding_creates_patch_candidate_request": "request_from_finding_required",
        "patch_candidate_request_is_not_patch": "request_patch_boundary_required",
        "repair_recommendation_not_patch_permission": "repair_permission_boundary_required",
        "operator_approval_required": "operator_approval_required",
        "dry_run_apply_required_later": "dry_run_required",
        "rollback_plan_required": "rollback_required",
        "no_automatic_patching": "automatic_patching_forbidden",
        "no_live_mutation": "live_mutation_forbidden",
        "no_deployment": "deployment_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_patch_request_hashes": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "authority_granted",
        "tools_authorized",
        "automatic_patching_allowed",
        "patch_applied",
        "live_mutation_performed",
        "candidate_deployed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
