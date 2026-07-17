"""P30 gate validators."""

from __future__ import annotations


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


_COMMON_FORBIDDEN = (
    "acquired_claim_treated_as_truth",
    "acquisition_result_treated_as_belief",
    "source_treated_as_authority",
    "source_quality_treated_as_truth",
    "provenance_treated_as_authority",
    "acquisition_task_treated_as_action",
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


def validate_p30_0_gate(result: dict) -> dict:
    checks = {
        "policy_written": "policy_required",
        "candidate_written": "candidate_required",
        "task_written": "task_required",
        "source_written": "source_required",
        "result_written": "result_required",
        "acquired_claim_not_truth": "claim_truth_boundary",
        "acquisition_result_not_belief": "result_belief_boundary",
        "source_not_authority": "source_authority_boundary",
        "source_quality_not_truth": "source_quality_boundary",
        "provenance_not_authority": "provenance_authority_boundary",
        "task_not_action": "task_action_boundary",
        "no_live_web": "live_web_forbidden",
        "no_external_provider": "external_provider_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_auto_belief_promotion": "auto_belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p30_1_gate(result: dict) -> dict:
    checks = {
        "p30_0_green": "p30_0_required",
        "p29_consolidation_green": "p29_required",
        "tasks_built": "tasks_required",
        "tasks_fixture_only": "fixture_only_required",
        "tasks_sandbox_only": "sandbox_only_required",
        "task_not_action": "task_action_boundary",
        "no_live_web": "live_web_forbidden",
        "no_external_provider": "external_provider_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_auto_belief_promotion": "auto_belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p30_2_gate(result: dict) -> dict:
    checks = {
        "p30_1_green": "p30_1_required",
        "results_produced": "results_required",
        "refusals_produced": "refusals_required",
        "all_refusal_reasons_covered": "all_refusal_reasons_required",
        "unsourced_normalized": "unsourced_normalization_required",
        "operator_review_created": "operator_review_required",
        "acquired_claim_not_truth": "claim_truth_boundary",
        "acquisition_result_not_belief": "result_belief_boundary",
        "no_live_web": "live_web_forbidden",
        "no_external_provider": "external_provider_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_auto_belief_promotion": "auto_belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}


def validate_p30_3_gate(result: dict) -> dict:
    checks = {
        "p30_2_green": "p30_2_required",
        "iteration_count_met": "iteration_count_required",
        "stable_hashes_match": "stable_hashes_required",
        "mutation_detected_task": "mutation_task_required",
        "mutation_detected_source": "mutation_source_required",
        "mutation_detected_truth_promotion": "mutation_truth_promotion_required",
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


def validate_p30_consolidation_gate(result: dict) -> dict:
    checks = {
        "p30_0_green": "p30_0_required",
        "p30_1_green": "p30_1_required",
        "p30_2_green": "p30_2_required",
        "p30_3_green": "p30_3_required",
        "p26_green": "p26_required",
        "p27_green": "p27_required",
        "p28_green": "p28_required",
        "p29_green": "p29_required",
        "acquired_claim_not_truth": "claim_truth_boundary",
        "acquisition_result_not_belief": "result_belief_boundary",
        "source_not_authority": "source_authority_boundary",
        "task_not_action": "task_action_boundary",
        "no_live_web": "live_web_forbidden",
        "no_external_provider": "external_provider_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_auto_belief_promotion": "auto_belief_promotion_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_deletion": "deletion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(result, _COMMON_FORBIDDEN)
    return {"ok": not failures, "failures": failures}
