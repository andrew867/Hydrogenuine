"""DTX gate validators."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import VERDICT_RED_DTX0


def _check(result: dict, checks: dict[str, str]) -> list[str]:
    return [failure for key, failure in checks.items() if not result.get(key)]


def _forbidden(result: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if result.get(key)]


def validate_dtx0_gate(result: dict) -> dict:
    checks = {
        "dib_consolidation_green": "dib_consolidation_required",
        "schemas_declared": "schemas_required",
        "exchange_written": "exchange_required",
        "manifest_written": "manifest_required",
        "fixture_written": "fixture_required",
        "outcome_written": "outcome_required",
        "extraction_written": "extraction_required",
        "bridge_written": "bridge_required",
        "packet_written": "packet_required",
        "policy_written": "policy_required",
        "exchange_not_truth": "exchange_truth_boundary",
        "extracted_not_truth": "extracted_truth_boundary",
        "adapter_not_promotion": "adapter_promotion_boundary",
        "packet_not_approval": "packet_approval_boundary",
        "replay_not_truth": "replay_truth_boundary",
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
            "document_exchange_treated_as_truth",
            "extracted_text_treated_as_truth",
            "dib_adapter_treated_as_belief_promotion",
            "belief_promotion_automatic",
            "pdf_ingestion_enabled",
            "ocr_ingestion_enabled",
            "html_parsing_enabled",
            "arbitrary_file_ingestion_enabled",
        ),
    )
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_DTX0, "failures": failures}


def validate_dtx1_gate(result: dict) -> dict:
    checks = {
        "dib_consolidation_green": "dib_consolidation_required",
        "dtx0_green": "dtx0_required",
        "all_families_present": "families_required",
        "manifest_written": "manifest_required",
        "fixtures_written": "fixtures_required",
        "outcomes_written": "outcomes_required",
        "validation_passed": "validation_required",
        "corpus_not_truth": "corpus_truth_boundary",
        "outcome_not_proof": "outcome_proof_boundary",
        "duplicate_not_corroboration": "duplicate_corroboration_boundary",
        "stale_not_false": "stale_false_boundary",
        "no_pdf_ocr_html_binary": "pdf_ocr_html_binary_forbidden",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_manifest_hash": "replay_manifest_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        ("document_corpus_treated_as_world", "expected_outcome_treated_as_proof", "duplicate_treated_as_corroboration"),
    )
    return {"ok": not failures, "failures": failures}


def validate_dtx2_gate(result: dict) -> dict:
    checks = {
        "dib_consolidation_green": "dib_consolidation_required",
        "dtx1_green": "dtx1_required",
        "explicit_manifest_only": "explicit_manifest_required",
        "receipts_written": "receipts_required",
        "failures_written": "failures_required",
        "bridge_written": "bridge_required",
        "receipt_not_truth": "receipt_truth_boundary",
        "bridge_not_promotion": "bridge_promotion_boundary",
        "identity_not_filename": "filename_identity_boundary",
        "metadata_not_provenance": "metadata_provenance_boundary",
        "hash_not_truth": "hash_truth_boundary",
        "no_pdf_ocr": "pdf_ocr_forbidden",
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
        ("extracted_text_treated_as_truth", "dib_adapter_treated_as_belief_promotion", "belief_promotion_automatic"),
    )
    return {"ok": not failures, "failures": failures}


def validate_dtx3_gate(result: dict) -> dict:
    checks = {
        "dib_consolidation_green": "dib_consolidation_required",
        "dtx2_green": "dtx2_required",
        "packets_written": "packets_required",
        "second_source_written": "second_source_required",
        "contradiction_written": "contradiction_required",
        "dashboard_written": "dashboard_required",
        "packet_not_truth": "packet_truth_boundary",
        "second_source_not_truth": "second_source_truth_boundary",
        "contradiction_not_resolution": "contradiction_resolution_boundary",
        "dashboard_not_approval": "dashboard_approval_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_deterministic": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        ("packet_treated_as_truth", "second_source_result_treated_as_truth", "contradiction_record_treated_as_resolution"),
    )
    return {"ok": not failures, "failures": failures}


def validate_dtx4_gate(result: dict) -> dict:
    checks = {
        "dib_consolidation_green": "dib_consolidation_required",
        "dtx3_green": "dtx3_required",
        "iteration_count_met": "iteration_count_required",
        "all_iterations_match": "iteration_match_required",
        "stable_hashes_written": "stable_hashes_required",
        "mutation_probes_written": "mutation_probes_required",
        "mutation_results_written": "mutation_results_required",
        "mismatches_detected": "mismatch_detection_required",
        "soak_not_truth": "soak_truth_boundary",
        "replay_not_truth": "replay_truth_boundary",
        "mutation_not_repair": "mutation_repair_boundary",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_web_or_provider": "web_provider_forbidden",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    failures = _check(result, checks) + _forbidden(
        result,
        ("soak_treated_as_truth", "replay_match_treated_as_truth", "mutation_auto_repaired"),
    )
    return {"ok": not failures, "failures": failures}


def validate_dtx_consolidation_gate(result: dict) -> dict:
    checks = {
        "all_dtx_phases_green": "all_dtx_phases_required",
        "dib_consolidation_linked": "dib_consolidation_required",
        "proof_bundles_linked": "proof_bundles_required",
        "reports_linked": "reports_required",
        "tests_linked": "tests_required",
        "gates_linked": "gates_required",
        "safe_text_markdown_only": "safe_text_markdown_required",
        "pdf_disabled": "pdf_disabled_required",
        "ocr_disabled": "ocr_disabled_required",
        "no_arbitrary_ingestion": "arbitrary_ingestion_forbidden",
        "no_document_as_truth": "document_truth_boundary",
        "no_extracted_text_as_truth": "extracted_text_truth_boundary",
        "no_adapter_as_promotion": "adapter_promotion_boundary",
        "no_packet_as_truth": "packet_truth_boundary",
        "no_replay_match_as_truth": "replay_match_truth_boundary",
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
    failures = _check(result, checks) + _forbidden(
        result,
        (
            "document_exchange_treated_as_truth",
            "extracted_text_treated_as_truth",
            "dib_adapter_treated_as_belief_promotion",
            "packet_treated_as_truth",
            "replay_match_treated_as_truth",
            "belief_promotion_automatic",
            "pdf_ingestion_enabled",
            "ocr_ingestion_enabled",
            "deletion_performed",
        ),
    )
    return {"ok": not failures, "failures": failures}
