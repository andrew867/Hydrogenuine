"""EWP schema foundation and phase gate validation."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import VERDICT_RED_EWP0


def validate_ewp0_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp_consolidation_green": "sqp_consolidation_required",
        "schemas_declared": "schemas_required",
        "workbench_packet_written": "workbench_packet_required",
        "claim_packet_written": "claim_packet_required",
        "source_summary_written": "source_summary_required",
        "support_record_written": "support_record_required",
        "contradiction_record_written": "contradiction_record_required",
        "second_source_requirement_written": "second_source_requirement_required",
        "second_source_result_written": "second_source_result_required",
        "contradiction_review_packet_written": "contradiction_review_packet_required",
        "review_status_written": "review_status_required",
        "dashboard_written": "dashboard_required",
        "packet_not_truth": "packet_truth_boundary",
        "packet_not_authority": "packet_authority_boundary",
        "packet_not_approval": "packet_approval_boundary",
        "support_not_proof": "support_proof_boundary",
        "contradiction_not_resolution": "contradiction_resolution_boundary",
        "second_source_not_truth": "second_source_truth_boundary",
        "dashboard_not_approval": "dashboard_approval_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_authority": "authority_forbidden",
        "no_tools": "tools_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "packet_treated_as_truth",
        "packet_treated_as_authority",
        "packet_treated_as_approval",
        "support_record_treated_as_proof",
        "contradiction_record_treated_as_resolution",
        "second_source_result_treated_as_truth",
        "dashboard_treated_as_operator_approval",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_EWP0, "failures": failures}


def validate_ewp1_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp_consolidation_green": "sqp_consolidation_required",
        "ewp0_green": "ewp0_required",
        "leb_claim_links_consumed": "leb_claim_links_required",
        "orp_reviewed_links_consumed": "orp_reviewed_links_required",
        "orp_belief_revisions_consumed": "orp_belief_revisions_required",
        "sqp_fingerprints_consumed": "sqp_fingerprints_required",
        "sqp_duplicates_consumed": "sqp_duplicates_required",
        "sqp_quality_consumed": "sqp_quality_required",
        "sqp_provenance_consumed": "sqp_provenance_required",
        "sqp_staleness_conflicts_consumed": "sqp_staleness_conflicts_required",
        "sqp_review_hints_consumed": "sqp_review_hints_required",
        "claim_packets_written": "claim_packets_required",
        "source_summaries_written": "source_summaries_required",
        "support_records_written": "support_records_required",
        "contradiction_records_written": "contradiction_records_required",
        "packet_not_truth": "packet_truth_boundary",
        "support_not_proof": "support_proof_boundary",
        "quality_not_authority": "quality_authority_boundary",
        "provenance_not_proof": "provenance_proof_boundary",
        "contradictions_visible": "contradiction_visibility_boundary",
        "duplicates_collapsed_originals_preserved": "duplicate_collapse_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tools_actions_live_effects": "effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_packet_hashes": "replay_packet_hashes_required",
        "replay_preserves_manifest_hash": "replay_manifest_hash_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "packet_treated_as_truth",
        "support_record_treated_as_proof",
        "source_quality_treated_as_truth",
        "provenance_treated_as_authority",
        "duplicate_treated_as_corroboration",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_ewp2_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "ewp0_green": "ewp0_required",
        "ewp1_green": "ewp1_required",
        "claim_packets_consumed": "claim_packets_required",
        "requirements_written": "requirements_required",
        "results_written": "results_required",
        "all_outcomes_exercised": "outcomes_required",
        "second_source_not_truth": "second_source_truth_boundary",
        "second_source_missing_not_false": "missing_not_false_boundary",
        "duplicate_not_corroboration": "duplicate_corroboration_boundary",
        "independent_not_certainty": "independent_not_certainty_boundary",
        "review_ready_not_approval": "review_ready_approval_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tools_actions_live_effects": "effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_result_hashes": "replay_result_hashes_required",
        "replay_preserves_manifest_hash": "replay_manifest_hash_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "second_source_result_treated_as_truth",
        "duplicate_treated_as_corroboration",
        "dashboard_treated_as_operator_approval",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_ewp3_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "ewp1_green": "ewp1_required",
        "claim_packets_consumed": "claim_packets_required",
        "contradiction_packets_written": "contradiction_packets_required",
        "cluster_packets_written": "cluster_packets_required",
        "contradiction_not_resolution": "contradiction_resolution_boundary",
        "cluster_not_proof": "cluster_proof_boundary",
        "contradicted_source_preserved": "source_preservation_boundary",
        "stale_not_false": "stale_false_boundary",
        "quarantine_not_deletion": "quarantine_deletion_boundary",
        "operator_review_required": "operator_review_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tools_actions_live_effects": "effects_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_packet_hashes": "replay_packet_hashes_required",
        "replay_preserves_manifest_hash": "replay_manifest_hash_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "contradiction_record_treated_as_resolution",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "deletion_performed",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_ewp4_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "ewp1_green": "ewp1_required",
        "ewp2_green": "ewp2_required",
        "ewp3_green": "ewp3_required",
        "claim_packets_consumed": "claim_packets_required",
        "second_source_results_consumed": "second_source_results_required",
        "contradiction_packets_consumed": "contradiction_packets_required",
        "dashboard_written": "dashboard_required",
        "dashboard_md_written": "dashboard_md_required",
        "review_statuses_written": "review_statuses_required",
        "dashboard_not_approval": "dashboard_approval_boundary",
        "dashboard_not_truth": "dashboard_truth_boundary",
        "dashboard_cannot_authorize_action": "dashboard_action_boundary",
        "dashboard_cannot_authorize_tool": "dashboard_tool_boundary",
        "dashboard_cannot_promote_belief": "dashboard_belief_boundary",
        "dashboard_cannot_hide_contradictions": "dashboard_contradiction_boundary",
        "dashboard_cannot_delete": "dashboard_deletion_boundary",
        "no_live_ui": "live_ui_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_dashboard_hash": "replay_dashboard_hash_required",
        "replay_preserves_manifest_hash": "replay_manifest_hash_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "dashboard_treated_as_operator_approval",
        "packet_treated_as_truth",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "deletion_performed",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "live_ui_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_ewp_consolidation_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "reviewed_beta_green": "reviewed_beta_required",
        "sqp_consolidation_green": "sqp_consolidation_required",
        "ewp0_green": "ewp0_required",
        "ewp1_green": "ewp1_required",
        "ewp2_green": "ewp2_required",
        "ewp3_green": "ewp3_required",
        "ewp4_green": "ewp4_required",
        "no_truth_claim": "truth_claim_forbidden",
        "no_authority": "authority_forbidden",
        "no_second_source_as_truth": "second_source_truth_forbidden",
        "no_contradiction_as_resolution": "contradiction_resolution_forbidden",
        "no_dashboard_as_approval": "dashboard_approval_forbidden",
        "no_automatic_belief_promotion": "belief_promotion_forbidden",
        "no_web_provider_live_effect": "web_provider_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    return {"ok": not failures, "failures": failures}
