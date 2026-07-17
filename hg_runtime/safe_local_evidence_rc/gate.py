"""SLE-RC gate validators."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.schemas import (
    BOUNDARY_ASSERTION_IDS,
    COMPONENT_FAMILIES,
    RECORD_TYPES,
    VERDICT_RED_SLE_RC0,
    VERDICT_RED_SLE_RC1,
    VERDICT_RED_SLE_RC2,
    VERDICT_RED_SLE_RC3,
    VERDICT_RED_SLE_RC_CONSOLIDATION,
    VERDICT_RED_SLE_RC_EXTENDED,
)


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


def validate_sle_rc0_gate(result: dict) -> dict:
    checks = {
        "schemas_declared": "schemas_required",
        "rc_written": "rc_required",
        "manifest_written": "manifest_required",
        "status_written": "status_required",
        "assertion_written": "assertion_required",
        "artifact_index_written": "artifact_index_required",
        "risk_written": "risk_required",
        "rc_not_deployment": "rc_deployment_boundary",
        "rc_green_not_truth": "rc_truth_boundary",
        "rc_green_not_authority": "rc_authority_boundary",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "release_candidate_is_deployment",
            "rc_green_is_truth",
            "rc_green_is_authority",
            "rc_green_is_live_permission",
            "belief_promotion_automatic",
            "pdf_ingestion_enabled",
            "ocr_ingestion_enabled",
            "html_parsing_enabled",
            "arbitrary_file_ingestion_enabled",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_SLE_RC0, "failures": failures}


def validate_sle_rc1_gate(result: dict) -> dict:
    checks = {
        "sle_rc0_green": "sle_rc0_required",
        "artifact_index_written": "artifact_index_required",
        "component_statuses_written": "component_statuses_required",
        "proof_bundle_index_written": "proof_bundle_index_required",
        "report_index_written": "report_index_required",
        "gate_statuses_written": "gate_statuses_required",
        "all_consolidations_present": "consolidations_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "green_not_inferred_from_presence": "presence_inference_forbidden",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        ("green_inferred_from_presence_only", "rc_green_is_truth", "rc_green_is_authority"),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_SLE_RC1, "failures": failures}


def validate_sle_rc2_gate(result: dict) -> dict:
    checks = {
        "sle_rc1_green": "sle_rc1_required",
        "boundary_matrix_written": "boundary_matrix_required",
        "assertions_written": "assertions_required",
        "all_assertions_present": "all_assertions_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks)
    if result.get("boundary_failure_count", 0) > 0:
        failures.append("boundary_failures_present")
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_SLE_RC2, "failures": failures}


def validate_sle_rc3_gate(result: dict) -> dict:
    checks = {
        "sle_rc2_green": "sle_rc2_required",
        "soak_iterations_written": "soak_iterations_required",
        "minimum_iterations_met": "minimum_iterations_required",
        "stable_hashes_written": "stable_hashes_required",
        "replay_result_written": "replay_result_required",
        "mutation_summary_written": "mutation_summary_required",
        "soak_not_truth": "soak_truth_boundary",
        "replay_not_truth": "replay_truth_boundary",
        "mutation_not_repair": "mutation_repair_boundary",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "soak_treated_as_truth",
            "replay_match_treated_as_truth",
            "mutation_auto_repaired",
            "belief_promotion_automatic",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_SLE_RC3, "failures": failures}


def validate_sle_rc_consolidation_gate(result: dict) -> dict:
    checks = {
        "all_sle_rc_phases_green": "sle_rc_phases_required",
        "all_component_families_linked": "component_families_required",
        "artifact_index_linked": "artifact_index_required",
        "boundary_matrix_linked": "boundary_matrix_required",
        "soak_summary_linked": "soak_summary_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "no_deployment_claim": "deployment_claim_forbidden",
        "no_truth_claim": "truth_claim_forbidden",
        "no_action_authorization": "action_authorization_forbidden",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "release_candidate_is_deployment",
            "rc_green_is_truth",
            "rc_green_is_authority",
            "rc_green_is_live_permission",
            "belief_promotion_automatic",
            "deletion_performed",
            "patch_request_applied",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_SLE_RC_CONSOLIDATION, "failures": failures}


def validate_sle_rc_extended_gate(result: dict) -> dict:
    checks = {
        "sle_rc_consolidation_green": "sle_rc_consolidation_required",
        "minimum_iterations_met": "minimum_iterations_required",
        "extended_iterations_written": "extended_iterations_required",
        "stable_hashes_written": "stable_hashes_required",
        "churn_analysis_written": "churn_analysis_required",
        "boundary_matrix_replays_written": "boundary_matrix_replays_required",
        "extended_replay_result_written": "extended_replay_result_required",
        "regression_matrix_written": "regression_matrix_required",
        "all_iterations_match": "iterations_match_required",
        "iterations_stable": "iterations_stable_required",
        "boundary_matrix_stable": "boundary_matrix_stable_required",
        "regression_all_paths_green": "regression_paths_required",
        "oec_corpus_path_included": "oec_path_required",
        "dtx_safe_text_path_included": "dtx_path_required",
        "oes_mutation_summary_path_included": "oes_path_required",
        "no_unexpected_churn": "unexpected_churn_present",
        "soak_not_truth": "soak_truth_boundary",
        "replay_not_truth": "replay_truth_boundary",
        "mutation_not_repair": "mutation_repair_boundary",
        "no_new_ingestion_capability": "new_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_html": "html_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "unexpected_churn_detected",
            "soak_treated_as_truth",
            "replay_match_treated_as_truth",
            "mutation_auto_repaired",
            "belief_promotion_automatic",
            "pdf_ingestion_enabled",
            "ocr_ingestion_enabled",
            "html_parsing_enabled",
            "arbitrary_file_ingestion_enabled",
            "release_candidate_is_deployment",
            "rc_green_is_truth",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_SLE_RC_EXTENDED, "failures": failures}


def required_record_types_present() -> bool:
    required = {
        "safe_local_evidence_rc_v1",
        "rc_manifest_v1",
        "rc_component_status_v1",
        "rc_boundary_assertion_v1",
        "rc_artifact_index_v1",
        "rc_release_risk_record_v1",
        "rc_gate_result_v1",
    }
    return required <= RECORD_TYPES


def required_boundary_assertions_present(assertions: list[dict]) -> bool:
    keys = {row["assertion_key"] for row in assertions}
    return set(BOUNDARY_ASSERTION_IDS) <= keys


def required_component_families_present(statuses: list[dict]) -> bool:
    families = {row["component_family"] for row in statuses}
    return set(COMPONENT_FAMILIES) <= families
