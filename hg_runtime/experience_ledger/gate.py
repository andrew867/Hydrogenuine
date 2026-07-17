"""P26-0 gate validation."""

from __future__ import annotations

from hg_runtime.experience_ledger.schemas import (
    VERDICT_RED_P26_0,
    VERDICT_RED_P26_1,
    VERDICT_RED_P26_2,
    VERDICT_RED_P26_3,
    VERDICT_RED_P26_4,
    VERDICT_RED_P26_CONSOLIDATION,
)


def validate_p26_0_gate(result: dict) -> dict:
    failures: list[str] = []
    required_true = {
        "schemas_declared": "schemas_required",
        "policy_defaults_declared": "policy_defaults_required",
        "invariants_declared": "invariants_required",
        "experience_records_written": "experience_records_required",
        "memory_records_written": "memory_records_required",
        "recall_queries_written": "recall_queries_required",
        "recall_results_written": "recall_results_required",
        "promotion_requests_written": "promotion_requests_required",
        "promotion_decisions_written": "promotion_decisions_required",
        "retraction_records_written": "retraction_records_required",
        "memory_is_not_truth": "memory_truth_boundary",
        "recall_is_not_authority": "recall_authority_boundary",
        "experience_is_not_evidence_by_itself": "experience_evidence_boundary",
        "ledger_entry_is_not_belief": "ledger_belief_boundary",
        "promotion_request_is_not_promotion": "request_promotion_boundary",
        "operator_review_is_not_truth": "operator_review_truth_boundary",
        "provenance_required_for_recall": "recall_provenance_required",
        "source_quality_is_not_truth": "source_quality_truth_boundary",
        "retraction_is_not_erasure": "retraction_erasure_boundary",
        "quarantine_is_not_deletion": "quarantine_deletion_boundary",
        "no_automatic_belief_promotion": "auto_promotion_forbidden",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_schema_hashes": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in required_true.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "memory_treated_as_truth",
        "recall_treated_as_authority",
        "experience_treated_as_evidence_by_itself",
        "ledger_entry_treated_as_belief",
        "promotion_request_auto_applied",
        "orp_bypassed",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "tool_authorization_granted",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "ocr_enabled",
        "html_parsing_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P26_0, "failures": failures}


def validate_p26_1_gate(result: dict) -> dict:
    failures: list[str] = []
    required_true = {
        "explicit_artifact_manifest_only": "explicit_manifest_required",
        "sle_rc_artifact_mapped": "sle_rc_artifact_required",
        "phase25_artifact_mapped": "phase25_artifact_required",
        "p26_gap_artifact_mapped": "p26_gap_artifact_required",
        "experience_records_written": "experience_records_required",
        "memory_records_written": "memory_records_required",
        "provenance_pointers_recorded": "provenance_required",
        "source_quality_pointers_recorded": "source_quality_pointer_required",
        "boundary_tags_recorded": "boundary_tags_required",
        "retraction_capability_recorded": "retraction_required",
        "quarantine_capability_recorded": "quarantine_required",
        "stable_hash_chain_written": "hash_chain_required",
        "replay_verification_passed": "replay_required",
        "append_only_ledger": "append_only_required",
        "memory_is_not_truth": "memory_truth_boundary",
        "experience_is_not_evidence_by_itself": "experience_evidence_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_action_authorization": "action_authorization_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in required_true.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "memory_treated_as_truth",
        "experience_treated_as_evidence_by_itself",
        "belief_promoted",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "ocr_enabled",
        "html_parsing_enabled",
        "deletion_performed",
        "patch_request_applied",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P26_1, "failures": failures}


def validate_p26_2_gate(result: dict) -> dict:
    failures: list[str] = []
    required_true = {
        "recall_query_types_declared": "query_types_required",
        "recall_index_written": "index_required",
        "recall_queries_written": "queries_required",
        "recall_results_written": "results_required",
        "recall_manifest_written": "manifest_required",
        "recall_returns_provenance_pointers": "provenance_required",
        "recall_read_only": "read_only_required",
        "memory_is_not_truth": "memory_truth_boundary",
        "recall_is_not_authority": "recall_authority_boundary",
        "recall_cannot_authorize_tools": "tool_boundary",
        "recall_cannot_promote_beliefs": "promotion_boundary",
        "recall_cannot_delete": "deletion_boundary",
        "retracted_memory_handled": "retracted_memory_required",
        "quarantined_memory_handled": "quarantined_memory_required",
        "replay_stable": "replay_required",
        "fake_truth_authority_rejected": "fake_green_required",
        "secret_redaction_passed": "redaction_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in required_true.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "memory_treated_as_truth",
        "recall_treated_as_authority",
        "authority_granted",
        "tools_authorized",
        "belief_promoted",
        "belief_promotion_automatic",
        "deletion_performed",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "ocr_enabled",
        "html_parsing_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P26_2, "failures": failures}


def validate_p26_3_gate(result: dict) -> dict:
    failures: list[str] = []
    required_true = {
        "promotion_requests_written": "requests_required",
        "promotion_decisions_written": "decisions_required",
        "promotion_rejections_written": "rejections_required",
        "orp_memory_bridge_manifest_written": "manifest_required",
        "creates_request_from_memory_record": "request_from_memory_required",
        "request_includes_memory_id": "memory_id_required",
        "request_includes_provenance_pointer": "provenance_required",
        "promotion_request_is_not_promotion": "request_not_promotion",
        "orp_decision_required": "orp_decision_required",
        "automatic_promotion_rejected": "automatic_promotion_rejected",
        "memory_as_truth_rejected": "memory_truth_rejected",
        "recall_as_authority_rejected": "recall_authority_rejected",
        "missing_provenance_rejected": "missing_provenance_rejected",
        "quarantined_memory_review_only": "quarantined_review_only_required",
        "reject_decision_supported": "reject_required",
        "defer_decision_supported": "defer_required",
        "approved_for_review_without_truth_claim": "approval_boundary_required",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_deletion": "deletion_forbidden",
        "no_orp_bypass": "orp_bypass_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_stable": "replay_required",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in required_true.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "memory_treated_as_truth",
        "recall_treated_as_authority",
        "promotion_request_auto_applied",
        "belief_promoted",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "tool_authorization_granted",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "orp_bypassed",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "ocr_enabled",
        "html_parsing_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P26_3, "failures": failures}


def validate_p26_4_gate(result: dict) -> dict:
    failures: list[str] = []
    required_true = {
        "soak_iterations_written": "iterations_required",
        "at_least_5_iterations": "five_iterations_required",
        "stable_hashes_written": "stable_hashes_required",
        "stable_hashes_match_across_iterations": "stable_hash_mismatch",
        "timestamp_proof_path_noise_excluded": "noise_exclusion_required",
        "memory_mutation_detected": "memory_mutation_required",
        "provenance_mutation_detected": "provenance_mutation_required",
        "promotion_decision_mutation_detected": "promotion_decision_mutation_required",
        "mutation_not_auto_repaired": "no_auto_repair_required",
        "original_artifacts_not_mutated": "original_artifacts_mutated",
        "replay_stable": "replay_required",
        "memory_is_not_truth": "memory_truth_boundary",
        "recall_is_not_authority": "recall_authority_boundary",
        "promotion_request_is_not_promotion": "request_promotion_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_orp_bypass": "orp_bypass_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in required_true.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "memory_treated_as_truth",
        "recall_treated_as_authority",
        "promotion_request_auto_applied",
        "belief_promoted",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "tool_authorization_granted",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "orp_bypassed",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "ocr_enabled",
        "html_parsing_enabled",
        "mutation_auto_repair_performed",
        "original_artifacts_mutated",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P26_4, "failures": failures}


def validate_p26_consolidation_gate(result: dict) -> dict:
    failures: list[str] = []
    required_true = {
        "p26_0_green": "p26_0_required",
        "p26_1_green": "p26_1_required",
        "p26_2_green": "p26_2_required",
        "p26_3_green": "p26_3_required",
        "p26_4_green": "p26_4_required",
        "exact_p26_gate_exists": "exact_gate_required",
        "component_index_written": "component_index_required",
        "boundary_matrix_written": "boundary_matrix_required",
        "consolidation_summary_written": "summary_required",
        "memory_is_not_truth": "memory_truth_boundary",
        "recall_is_not_authority": "recall_authority_boundary",
        "experience_is_not_evidence_by_itself": "experience_evidence_boundary",
        "ledger_entry_is_not_belief": "ledger_belief_boundary",
        "promotion_request_is_not_promotion": "request_promotion_boundary",
        "orp_gated_promotion_only": "orp_gate_required",
        "retraction_quarantine_supported": "retraction_quarantine_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in required_true.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "memory_treated_as_truth",
        "recall_treated_as_authority",
        "experience_treated_as_evidence_by_itself",
        "ledger_entry_treated_as_belief",
        "promotion_request_auto_applied",
        "belief_promoted",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "tool_authorization_granted",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "orp_bypassed",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "ocr_enabled",
        "html_parsing_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P26_CONSOLIDATION, "failures": failures}
