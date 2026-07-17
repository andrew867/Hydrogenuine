"""DIB gate validators."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import VERDICT_RED_DIB0


def validate_dib0_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oes_consolidation_green": "oes_consolidation_required",
        "schemas_declared": "schemas_required",
        "policy_written": "policy_required",
        "manifest_written": "manifest_required",
        "parser_policy_written": "parser_policy_required",
        "classification_written": "classification_required",
        "quarantine_written": "quarantine_required",
        "redaction_written": "redaction_required",
        "extraction_written": "extraction_required",
        "source_identity_written": "source_identity_required",
        "provenance_written": "provenance_required",
        "document_not_truth": "document_truth_boundary",
        "parsed_text_not_truth": "parsed_text_truth_boundary",
        "ocr_text_not_truth": "ocr_text_truth_boundary",
        "metadata_not_provenance": "metadata_provenance_boundary",
        "filename_not_identity": "filename_identity_boundary",
        "parser_success_not_correctness": "parser_correctness_boundary",
        "quarantine_not_deletion": "quarantine_deletion_boundary",
        "redaction_not_erasure": "redaction_erasure_boundary",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tool_authorization": "tool_authorization_forbidden",
        "no_parser_execution": "parser_execution_forbidden",
        "no_content_extraction": "content_extraction_forbidden",
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
        "document_treated_as_truth",
        "parsed_text_treated_as_truth",
        "ocr_text_treated_as_truth",
        "metadata_treated_as_provenance",
        "filename_treated_as_source_identity",
        "parser_success_treated_as_correctness",
        "classification_granted_trust",
        "belief_promotion_automatic",
        "pdf_ingestion_enabled",
        "ocr_ingestion_enabled",
        "arbitrary_file_ingestion_enabled",
        "parser_execution_enabled",
        "content_extraction_enabled",
        "deletion_performed",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_DIB0, "failures": failures}


def validate_dib1_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oes_consolidation_green": "oes_consolidation_required",
        "dib0_green": "dib0_required",
        "classifier_written": "classifier_required",
        "classifications_written": "classifications_required",
        "accepted_records_written": "accepted_records_required",
        "rejected_records_written": "rejected_records_required",
        "explicit_manifest_only": "explicit_manifest_required",
        "classification_not_trust": "classification_trust_boundary",
        "extension_not_truth": "extension_truth_boundary",
        "media_type_not_trust": "media_type_trust_boundary",
        "filename_not_identity": "filename_identity_boundary",
        "metadata_not_provenance": "metadata_provenance_boundary",
        "accepted_not_ingestion_approval": "accepted_approval_boundary",
        "rejected_not_deletion": "rejected_deletion_boundary",
        "pdf_rejected_disabled": "pdf_disabled_boundary",
        "ocr_rejected_disabled": "ocr_disabled_boundary",
        "no_parser_execution": "parser_execution_forbidden",
        "no_content_extraction": "content_extraction_forbidden",
        "no_pdf_ocr_enabled": "pdf_ocr_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tool_authorization": "tool_authorization_forbidden",
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
        "document_treated_as_truth",
        "classification_granted_trust",
        "parser_execution_authorized",
        "content_extraction_authorized",
        "belief_promotion_automatic",
        "pdf_ingestion_enabled",
        "ocr_ingestion_enabled",
        "deletion_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_dib2_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oes_consolidation_green": "oes_consolidation_required",
        "dib0_green": "dib0_required",
        "dib1_green": "dib1_required",
        "sandbox_policy_written": "sandbox_policy_required",
        "parser_registry_written": "parser_registry_required",
        "evaluations_written": "evaluations_required",
        "failures_written": "failures_required",
        "quarantine_written": "quarantine_required",
        "parser_disabled_by_default": "parser_disabled_required",
        "allowlist_explicit": "allowlist_required",
        "pdf_rejected": "pdf_rejected_required",
        "ocr_rejected": "ocr_rejected_required",
        "html_rejected": "html_rejected_required",
        "path_escape_rejected": "path_escape_required",
        "no_content_extraction": "content_extraction_forbidden",
        "no_parser_execution": "parser_execution_forbidden",
        "quarantine_not_deletion": "quarantine_deletion_boundary",
        "failure_not_deletion": "failure_deletion_boundary",
        "parser_success_not_correctness": "parser_correctness_boundary",
        "no_pdf_ocr_enabled": "pdf_ocr_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tool_authorization": "tool_authorization_forbidden",
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
        "document_treated_as_truth",
        "parsed_text_treated_as_truth",
        "extracted_text_treated_as_truth",
        "parser_success_treated_as_correctness",
        "belief_promotion_automatic",
        "pdf_ingestion_enabled",
        "ocr_ingestion_enabled",
        "deletion_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_dib3_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oes_consolidation_green": "oes_consolidation_required",
        "dib0_green": "dib0_required",
        "dib1_green": "dib1_required",
        "dib2_green": "dib2_required",
        "manifest_written": "manifest_required",
        "receipts_written": "receipts_required",
        "failures_written": "failures_required",
        "redaction_written": "redaction_required",
        "source_identity_written": "source_identity_required",
        "provenance_written": "provenance_required",
        "leb_adapter_written": "leb_adapter_required",
        "explicit_manifest_only": "explicit_manifest_required",
        "safe_text_markdown_only": "safe_text_markdown_required",
        "json_rejected_for_extraction": "json_rejection_required",
        "extracted_not_truth": "extracted_truth_boundary",
        "receipt_not_interpretation": "receipt_interpretation_boundary",
        "parser_success_not_correctness": "parser_correctness_boundary",
        "leb_adapter_not_belief_promotion": "leb_belief_boundary",
        "filename_not_identity": "filename_identity_boundary",
        "metadata_not_provenance": "metadata_provenance_boundary",
        "no_pdf_ocr_enabled": "pdf_ocr_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_tool_authorization": "tool_authorization_forbidden",
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
        "document_treated_as_truth",
        "parsed_text_treated_as_truth",
        "extracted_text_treated_as_truth",
        "parser_success_treated_as_correctness",
        "belief_promotion_automatic",
        "pdf_ingestion_enabled",
        "ocr_ingestion_enabled",
        "deletion_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_dib4_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oes_consolidation_green": "oes_consolidation_required",
        "dib0_green": "dib0_required",
        "dib1_green": "dib1_required",
        "dib2_green": "dib2_required",
        "dib3_green": "dib3_required",
        "policy_written": "policy_required",
        "rejections_written": "rejections_required",
        "manifest_written": "manifest_required",
        "pdf_ingestion_disabled": "pdf_ingestion_disabled_required",
        "pdf_extraction_disabled": "pdf_extraction_disabled_required",
        "pdf_metadata_not_provenance": "pdf_metadata_boundary",
        "pdf_filename_not_identity": "pdf_filename_boundary",
        "pdf_rejection_not_deletion": "pdf_rejection_deletion_boundary",
        "no_pdf_parser_dependency": "pdf_dependency_forbidden",
        "no_pdf_parsing": "pdf_parsing_forbidden",
        "no_content_extraction": "pdf_content_extraction_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
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
        "pdf_ingestion_enabled",
        "ocr_ingestion_enabled",
        "metadata_treated_as_provenance",
        "filename_treated_as_source_identity",
        "deletion_performed",
        "belief_promotion_automatic",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_dib5_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "oes_consolidation_green": "oes_consolidation_required",
        "dib0_green": "dib0_required",
        "dib1_green": "dib1_required",
        "dib2_green": "dib2_required",
        "dib3_green": "dib3_required",
        "dib4_green": "dib4_required",
        "policy_written": "policy_required",
        "rejections_written": "rejections_required",
        "manifest_written": "manifest_required",
        "ocr_disabled": "ocr_disabled_required",
        "ocr_confidence_not_truth": "ocr_confidence_boundary",
        "ocr_output_not_truth": "ocr_output_boundary",
        "ocr_rejection_not_deletion": "ocr_rejection_deletion_boundary",
        "no_ocr_dependency": "ocr_dependency_forbidden",
        "no_ocr_execution": "ocr_execution_forbidden",
        "no_image_parsing": "image_parsing_forbidden",
        "no_pdf_parsing": "pdf_parsing_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
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
        "ocr_ingestion_enabled",
        "ocr_text_treated_as_truth",
        "deletion_performed",
        "belief_promotion_automatic",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}


def validate_dib_consolidation_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "all_dib_phases_green": "all_dib_phases_required",
        "proof_bundles_linked": "proof_bundles_required",
        "reports_linked": "reports_required",
        "tests_linked": "tests_required",
        "gates_linked": "gates_required",
        "safe_text_markdown_only": "safe_text_markdown_required",
        "pdf_disabled": "pdf_disabled_required",
        "ocr_disabled": "ocr_disabled_required",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_document_as_truth": "document_truth_boundary",
        "no_parsed_text_as_truth": "parsed_text_truth_boundary",
        "no_extracted_text_as_truth": "extracted_text_truth_boundary",
        "no_parser_success_as_correctness": "parser_correctness_boundary",
        "no_metadata_as_provenance": "metadata_provenance_boundary",
        "no_filename_as_source_identity": "filename_identity_boundary",
        "no_automatic_belief_promotion": "belief_promotion_forbidden",
        "no_web_provider_live_effect": "web_provider_forbidden",
        "no_deletion": "deletion_forbidden",
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
        "document_treated_as_truth",
        "parsed_text_treated_as_truth",
        "extracted_text_treated_as_truth",
        "parser_success_treated_as_correctness",
        "metadata_treated_as_provenance",
        "filename_treated_as_source_identity",
        "belief_promotion_automatic",
        "pdf_ingestion_enabled",
        "ocr_ingestion_enabled",
        "arbitrary_file_ingestion_enabled",
        "deletion_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures, "failures": failures}
