"""P29 gate validators."""

from __future__ import annotations


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


_COMMON_FORBIDDEN = (
    "tool_plan_treated_as_permission",
    "tool_request_executed_live",
    "sandbox_result_treated_as_live",
    "dry_run_treated_as_live_effect",
    "tool_receipt_treated_as_authority",
    "domain_pack_treated_as_tool_permission",
    "tool_authorization_granted",
    "tools_authorized",
    "authority_granted",
    "belief_promotion_automatic",
    "live_external_side_effects_created",
    "web_browse_performed",
    "external_provider_calls_made",
    "patch_request_applied",
    "deletion_performed",
)


def validate_p29_0_gate(result: dict) -> dict:
    checks = {
        "policy_written": "policy_required",
        "request_written": "request_required",
        "plan_written": "plan_required",
        "sandbox_written": "sandbox_required",
        "receipt_written": "receipt_required",
        "tool_plan_not_permission": "tool_plan_permission_boundary",
        "tool_request_not_execution": "tool_request_execution_boundary",
        "sandbox_not_live": "sandbox_live_boundary",
        "dry_run_not_live": "dry_run_live_boundary",
        "receipt_not_authority": "receipt_authority_boundary",
        "domain_pack_no_tools": "domain_pack_tool_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_patch_application": "patch_application_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p29_1_gate(result: dict) -> dict:
    checks = {
        "p29_0_green": "p29_0_required",
        "p28_consolidation_green": "p28_required",
        "explicit_manifest_only": "explicit_manifest_required",
        "tool_plans_built": "tool_plans_required",
        "capability_gaps_recorded": "capability_gaps_required",
        "operator_approval_required": "operator_approval_required",
        "tool_plan_not_permission": "tool_plan_permission_boundary",
        "tool_request_not_execution": "tool_request_execution_boundary",
        "domain_pack_no_tools": "domain_pack_tool_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_patch_application": "patch_application_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p29_2_gate(result: dict) -> dict:
    checks = {
        "p29_1_green": "p29_1_required",
        "sandbox_results_produced": "sandbox_results_required",
        "refusals_produced": "refusals_required",
        "all_refusal_reasons_covered": "all_refusal_reasons_required",
        "no_live_execution": "live_execution_forbidden",
        "sandbox_not_live": "sandbox_live_boundary",
        "dry_run_not_live": "dry_run_live_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_patch_application": "patch_application_forbidden",
        "no_deletion": "deletion_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p29_3_gate(result: dict) -> dict:
    checks = {
        "p29_2_green": "p29_2_required",
        "iteration_count_met": "iteration_count_required",
        "stable_hashes_match": "stable_hashes_required",
        "mutation_detected_tool_plan": "mutation_tool_plan_required",
        "mutation_detected_sandbox": "mutation_sandbox_required",
        "mutation_detected_refusal_bypass": "mutation_refusal_bypass_required",
        "mutation_not_auto_repaired": "mutation_auto_repair_forbidden",
        "originals_not_mutated": "originals_preserved_required",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_patch_application": "patch_application_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p29_consolidation_gate(result: dict) -> dict:
    checks = {
        "p29_0_green": "p29_0_required",
        "p29_1_green": "p29_1_required",
        "p29_2_green": "p29_2_required",
        "p29_3_green": "p29_3_required",
        "p26_green": "p26_required",
        "p27_green": "p27_required",
        "p28_green": "p28_required",
        "tool_plan_not_permission": "tool_plan_permission_boundary",
        "tool_request_not_execution": "tool_request_execution_boundary",
        "sandbox_not_live": "sandbox_live_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_patch_application": "patch_application_forbidden",
        "no_deletion": "deletion_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}
