"""P27 batch gate validators."""

from __future__ import annotations

from hg_runtime.skill_graph.p27_schemas import (
    P27_INVARIANTS,
    RECORD_TYPES,
    VERDICT_RED_P27_0,
    VERDICT_RED_P27_1,
    VERDICT_RED_P27_2,
    VERDICT_RED_P27_3,
    VERDICT_RED_P27_CONSOLIDATION,
)


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


def validate_p27_0_gate(result: dict) -> dict:
    checks = {
        "schemas_declared": "schemas_required",
        "policy_written": "policy_required",
        "skill_written": "skill_required",
        "edge_written": "edge_required",
        "link_written": "link_required",
        "candidate_written": "candidate_required",
        "result_written": "result_required",
        "skill_not_authority": "skill_authority_boundary",
        "reuse_not_proof": "reuse_proof_boundary",
        "transfer_not_competence": "transfer_competence_boundary",
        "memory_source_required": "memory_source_required",
        "provenance_required": "provenance_required",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
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
            "skill_treated_as_authority",
            "transfer_treated_as_proof",
            "belief_promotion_automatic",
            "tools_authorized",
            "authority_granted",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P27_0, "failures": failures}


def validate_p27_1_gate(result: dict) -> dict:
    checks = {
        "p27_0_green": "p27_0_required",
        "p26_consolidation_green": "p26_required",
        "explicit_manifest_only": "explicit_manifest_required",
        "skills_extracted": "skills_required",
        "source_links_written": "source_links_required",
        "provenance_pointers_recorded": "provenance_required",
        "skill_not_authority": "skill_authority_boundary",
        "memory_not_truth": "memory_truth_boundary",
        "recall_not_authority": "recall_authority_boundary",
        "skill_without_provenance_rejected": "missing_provenance_rejected",
        "confidence_descriptive_only": "confidence_competence_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, ("skill_treated_as_authority", "belief_promotion_automatic"))
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P27_1, "failures": failures}


def validate_p27_2_gate(result: dict) -> dict:
    checks = {
        "p27_1_green": "p27_1_required",
        "graph_index_written": "graph_index_required",
        "edges_written": "edges_required",
        "transfer_candidates_written": "transfer_candidates_required",
        "negative_transfer_risk_recorded": "negative_transfer_risk_required",
        "transfer_not_proof": "transfer_proof_boundary",
        "competence_not_claimed": "competence_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, ("transfer_treated_as_proof", "skill_treated_as_authority"))
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P27_2, "failures": failures}


def validate_p27_3_gate(result: dict) -> dict:
    checks = {
        "p27_2_green": "p27_2_required",
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
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P27_3, "failures": failures}


def validate_p27_consolidation_gate(result: dict) -> dict:
    checks = {
        "all_p27_phases_green": "p27_phases_required",
        "skill_not_authority": "skill_authority_boundary",
        "transfer_not_proof": "transfer_proof_boundary",
        "no_competence_claim": "competence_boundary",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        ("skill_treated_as_authority", "transfer_treated_as_proof", "belief_promotion_automatic", "tools_authorized"),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P27_CONSOLIDATION, "failures": failures}
