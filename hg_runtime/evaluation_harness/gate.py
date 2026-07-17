"""P31 gate validators."""

from __future__ import annotations


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


_COMMON_FORBIDDEN = (
    "evaluation_treated_as_truth",
    "evaluation_treated_as_competence",
    "benchmark_treated_as_deployment_permission",
    "competence_claimed",
    "tool_authorization_granted",
    "tools_authorized",
    "authority_granted",
    "belief_promotion_automatic",
    "live_external_side_effects_created",
    "web_browse_performed",
    "external_provider_calls_made",
    "patch_request_applied",
    "deletion_performed",
    "arbitrary_file_ingestion_enabled",
    "pdf_ingestion_enabled",
    "ocr_enabled",
    "html_parsing_enabled",
)


def validate_p31_0_gate(result: dict) -> dict:
    checks = {
        "policy_written": "policy_required",
        "fixtures_written": "fixtures_required",
        "task_families_written": "task_families_required",
        "expected_observed_written": "expected_observed_required",
        "result_written": "result_required",
        "refusal_written": "refusal_required",
        "evaluation_is_not_truth": "evaluation_truth_boundary",
        "evaluation_is_not_competence": "evaluation_competence_boundary",
        "benchmark_is_not_deployment_permission": "benchmark_deployment_boundary",
        "no_tool_authorization": "tool_auth_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_pdf_ocr_html": "pdf_ocr_html_forbidden",
        "no_automatic_belief_promotion": "auto_belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p31_1_gate(result: dict) -> dict:
    checks = {
        "p31_0_green": "p31_0_required",
        "fixtures_consumed": "fixtures_required",
        "results_produced": "results_required",
        "task_family_coverage_recorded": "coverage_required",
        "gaps_recorded": "gaps_required",
        "score_not_truth": "score_truth_boundary",
        "family_not_general_competence": "family_competence_boundary",
        "no_live_providers": "live_providers_forbidden",
        "no_web": "web_forbidden",
        "no_tool_authorization": "tool_auth_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p31_2_gate(result: dict) -> dict:
    checks = {
        "p31_1_green": "p31_1_required",
        "refusals_produced": "refusals_required",
        "all_claim_types_covered": "all_claim_types_required",
        "receipts_produced": "receipts_required",
        "evaluation_is_not_truth": "evaluation_truth_boundary",
        "evaluation_is_not_competence": "evaluation_competence_boundary",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_pdf_ocr_html": "pdf_ocr_html_forbidden",
        "no_tool_authorization": "tool_auth_forbidden",
        "no_automatic_belief_promotion": "auto_belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p31_3_gate(result: dict) -> dict:
    checks = {
        "p31_2_green": "p31_2_required",
        "iteration_count_met": "iteration_count_required",
        "stable_hashes_match": "stable_hashes_required",
        "mutation_detected_fixture": "mutation_fixture_required",
        "mutation_detected_expected_observed": "mutation_expected_observed_required",
        "mutation_detected_fake_competence": "mutation_fake_competence_required",
        "mutation_not_auto_repaired": "mutation_auto_repair_forbidden",
        "originals_not_mutated": "originals_preserved_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p31_consolidation_gate(result: dict) -> dict:
    checks = {
        "p31_0_green": "p31_0_required",
        "p31_1_green": "p31_1_required",
        "p31_2_green": "p31_2_required",
        "p31_3_green": "p31_3_required",
        "p26_green": "p26_required",
        "p27_green": "p27_required",
        "p28_green": "p28_required",
        "p29_green": "p29_required",
        "p30_green": "p30_required",
        "evaluation_is_not_truth": "evaluation_truth_boundary",
        "evaluation_is_not_competence": "evaluation_competence_boundary",
        "benchmark_is_not_deployment_permission": "benchmark_deployment_boundary",
        "expected_observed_match_is_not_truth": "match_truth_boundary",
        "no_live_effects": "live_effects_forbidden",
        "no_web_provider": "web_provider_forbidden",
        "no_pdf_ocr_html": "pdf_ocr_html_forbidden",
        "no_tool_authorization": "tool_auth_forbidden",
        "no_automatic_belief_promotion": "auto_belief_promotion_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}
