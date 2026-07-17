"""OEC schema foundation and phase gate validation."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.schemas import VERDICT_RED_OEC0


def validate_oec0_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "ewp_consolidation_green": "ewp_consolidation_required",
        "schemas_declared": "schemas_required",
        "corpus_written": "corpus_required",
        "manifest_written": "manifest_required",
        "source_written": "source_required",
        "claim_written": "claim_required",
        "packet_written": "packet_required",
        "outcome_written": "outcome_required",
        "policy_written": "policy_required",
        "corpus_not_truth": "corpus_truth_boundary",
        "source_not_authority": "source_authority_boundary",
        "fixture_not_world": "fixture_world_boundary",
        "outcome_not_truth": "outcome_truth_boundary",
        "policy_no_arbitrary_ingestion": "arbitrary_ingestion_boundary",
        "no_pdf_ocr": "pdf_ocr_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_authority": "authority_forbidden",
        "no_tools": "tools_forbidden",
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
        "corpus_treated_as_truth",
        "corpus_source_treated_as_authority",
        "fixture_corpus_treated_as_world",
        "expected_outcome_treated_as_proof",
        "expected_outcome_treated_as_truth",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "directory_crawling_enabled",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_OEC0, "failures": failures}


def validate_oec1_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "ewp_consolidation_green": "ewp_consolidation_required",
        "oec0_green": "oec0_required",
        "all_families_present": "families_required",
        "manifest_written": "manifest_required",
        "sources_written": "sources_required",
        "claims_written": "claims_required",
        "outcomes_written": "outcomes_required",
        "validation_passed": "validation_required",
        "corpus_not_truth": "corpus_truth_boundary",
        "outcome_not_proof": "outcome_proof_boundary",
        "duplicate_not_corroboration": "duplicate_corroboration_boundary",
        "stale_not_false": "stale_false_boundary",
        "contradiction_not_resolved": "contradiction_resolution_boundary",
        "low_quality_not_deletion": "low_quality_deletion_boundary",
        "high_quality_not_certainty": "high_quality_certainty_boundary",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_manifest_hash": "replay_manifest_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "corpus_treated_as_truth",
        "expected_outcome_treated_as_proof",
        "duplicate_treated_as_corroboration",
        "stale_source_treated_as_false",
        "contradiction_record_treated_as_resolution",
        "belief_promotion_automatic",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_oec2_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "ewp_consolidation_green": "ewp_consolidation_required",
        "oec1_green": "oec1_required",
        "explicit_manifest_only": "explicit_manifest_required",
        "no_directory_crawling": "directory_crawl_forbidden",
        "no_path_traversal": "path_traversal_forbidden",
        "no_symlink_escape": "symlink_escape_forbidden",
        "no_pdf_ocr_binary": "pdf_ocr_binary_forbidden",
        "receipts_written": "receipts_required",
        "excerpts_written": "excerpts_required",
        "receipt_not_truth": "receipt_truth_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_receipt_hashes": "replay_receipt_hashes_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "corpus_treated_as_truth",
        "belief_promotion_automatic",
        "authority_granted",
        "tools_authorized",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "directory_crawling_enabled",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_oec3_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "ewp_consolidation_green": "ewp_consolidation_required",
        "oec2_green": "oec2_required",
        "claim_packets_written": "claim_packets_required",
        "second_source_results_written": "second_source_results_required",
        "contradiction_packets_written": "contradiction_packets_required",
        "dashboard_written": "dashboard_required",
        "packet_not_truth": "packet_truth_boundary",
        "second_source_not_truth": "second_source_truth_boundary",
        "contradiction_not_resolution": "contradiction_resolution_boundary",
        "dashboard_not_approval": "dashboard_approval_boundary",
        "expected_outcome_not_proof": "outcome_proof_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_manifest_hash": "replay_manifest_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "corpus_treated_as_truth",
        "expected_outcome_treated_as_proof",
        "packet_treated_as_truth",
        "second_source_result_treated_as_truth",
        "contradiction_record_treated_as_resolution",
        "dashboard_treated_as_operator_approval",
        "belief_promotion_automatic",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_oec_consolidation_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "ewp_consolidation_green": "ewp_consolidation_required",
        "oec0_green": "oec0_required",
        "oec1_green": "oec1_required",
        "oec2_green": "oec2_required",
        "oec3_green": "oec3_required",
        "no_corpus_as_truth": "corpus_truth_forbidden",
        "no_expected_outcome_as_proof": "outcome_proof_forbidden",
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
