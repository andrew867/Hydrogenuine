"""P28 batch gate validators."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.schemas import (
    P28_INVARIANTS,
    RECORD_TYPES,
    VERDICT_RED_BATCH_A,
    VERDICT_RED_P28_0,
    VERDICT_RED_P28_1,
    VERDICT_RED_P28_2,
    VERDICT_RED_P28_3,
    VERDICT_RED_P28_CONSOLIDATION,
)


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


def validate_p28_0_gate(result: dict) -> dict:
    checks = {
        "schemas_declared": "schemas_required",
        "policy_written": "policy_required",
        "pack_written": "pack_required",
        "link_written": "link_required",
        "boundary_written": "boundary_required",
        "readiness_written": "readiness_required",
        "domain_pack_not_permission": "pack_permission_boundary",
        "domain_label_not_expertise": "label_expertise_boundary",
        "readiness_not_deployment": "readiness_deployment_boundary",
        "skill_link_not_authority": "skill_link_authority_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "domain_pack_treated_as_permission",
            "domain_label_treated_as_expertise",
            "readiness_treated_as_deployment_permission",
            "skill_link_treated_as_authority",
            "tools_authorized",
            "authority_granted",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P28_0, "failures": failures}


def validate_p28_1_gate(result: dict) -> dict:
    checks = {
        "p28_0_green": "p28_0_required",
        "p27_consolidation_green": "p27_required",
        "explicit_manifest_only": "explicit_manifest_required",
        "domain_packs_built": "packs_required",
        "skill_links_written": "skill_links_required",
        "boundaries_written": "boundaries_required",
        "capability_map_written": "capability_map_required",
        "p27_manifest_consumed": "p27_manifest_required",
        "domain_pack_not_permission": "pack_permission_boundary",
        "domain_label_not_expertise": "label_expertise_boundary",
        "skill_link_not_authority": "skill_link_authority_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        ("domain_pack_treated_as_permission", "domain_label_treated_as_expertise", "skill_link_treated_as_authority"),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P28_1, "failures": failures}


def validate_p28_2_gate(result: dict) -> dict:
    checks = {
        "p28_1_green": "p28_1_required",
        "readiness_records_written": "readiness_required",
        "boundary_matrix_written": "boundary_matrix_required",
        "readiness_states_valid": "readiness_states_required",
        "readiness_not_deployment": "readiness_deployment_boundary",
        "refusal_boundary_enforced": "refusal_boundary_required",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        ("readiness_treated_as_deployment_permission", "domain_pack_treated_as_permission"),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P28_2, "failures": failures}


def validate_p28_3_gate(result: dict) -> dict:
    checks = {
        "p28_2_green": "p28_2_required",
        "iteration_count_met": "iteration_count_required",
        "all_iterations_match": "iterations_match_required",
        "stable_hashes_written": "stable_hashes_required",
        "mutation_probes_written": "mutation_probes_required",
        "mismatches_detected": "mismatches_required",
        "mutation_not_repair": "mutation_repair_boundary",
        "original_artifacts_not_mutated": "original_mutation_forbidden",
        "soak_not_proof": "soak_proof_boundary",
        "replay_not_truth": "replay_truth_boundary",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, ("mutation_auto_repaired",))
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P28_3, "failures": failures}


def validate_p28_consolidation_gate(result: dict) -> dict:
    checks = {
        "all_p28_phases_green": "p28_phases_required",
        "domain_pack_not_permission": "pack_permission_boundary",
        "domain_label_not_expertise": "label_expertise_boundary",
        "readiness_not_deployment": "readiness_deployment_boundary",
        "skill_link_not_authority": "skill_link_authority_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "domain_pack_treated_as_permission",
            "readiness_treated_as_deployment_permission",
            "skill_link_treated_as_authority",
            "tools_authorized",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P28_CONSOLIDATION, "failures": failures}


def validate_generalist_runtime_batch_a_gate(result: dict) -> dict:
    checks = {
        "p27_consolidation_green": "p27_consolidation_required",
        "p28_consolidation_green": "p28_consolidation_required",
        "component_index_written": "component_index_required",
        "boundary_matrix_written": "boundary_matrix_required",
        "domain_pack_not_permission": "pack_permission_boundary",
        "domain_label_not_expertise": "label_expertise_boundary",
        "readiness_not_deployment": "readiness_deployment_boundary",
        "skill_link_not_authority": "skill_link_authority_boundary",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "domain_pack_treated_as_permission",
            "readiness_treated_as_deployment_permission",
            "tools_authorized",
            "authority_granted",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_BATCH_A, "failures": failures}
