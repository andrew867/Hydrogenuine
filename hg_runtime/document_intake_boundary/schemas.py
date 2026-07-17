"""DIB schema foundation and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

DIB_APPROVED_FIXTURE_ROOT = "tests/fixtures/document_intake_boundary"

VERDICT_GREEN_DIB0 = "GREEN_DIB_0_BOUNDARY_SCHEMAS"
VERDICT_RED_DIB0 = "RED_DIB_0_BOUNDARY_SCHEMAS_FAILED"
VERDICT_GREEN_DIB1 = "GREEN_DIB_1_FILE_TYPE_CLASSIFIER"
VERDICT_RED_DIB1 = "RED_DIB_1_FILE_TYPE_CLASSIFIER_FAILED"
VERDICT_GREEN_DIB2 = "GREEN_DIB_2_PARSER_SANDBOX_QUARANTINE"
VERDICT_RED_DIB2 = "RED_DIB_2_PARSER_SANDBOX_QUARANTINE_FAILED"
VERDICT_GREEN_DIB3 = "GREEN_DIB_3_SAFE_TEXT_EXTRACTION"
VERDICT_RED_DIB3 = "RED_DIB_3_SAFE_TEXT_EXTRACTION_FAILED"
VERDICT_GREEN_DIB4 = "GREEN_DIB_4_PDF_DISABLED_GATE"
VERDICT_RED_DIB4 = "RED_DIB_4_PDF_DISABLED_GATE_FAILED"
VERDICT_GREEN_DIB5 = "GREEN_DIB_5_OCR_DISABLED_GATE"
VERDICT_RED_DIB5 = "RED_DIB_5_OCR_DISABLED_GATE_FAILED"
VERDICT_GREEN_DIB_CONSOLIDATION = "GREEN_DIB_DOCUMENT_INTAKE_BOUNDARY_CONSOLIDATION"
VERDICT_RED_DIB_CONSOLIDATION = "RED_DIB_DOCUMENT_INTAKE_BOUNDARY_CONSOLIDATION_FAILED"

PARSER_STATUSES = {
    "PARSER_ALLOWED_TEXT_ONLY",
    "PARSER_DISABLED_BY_DEFAULT",
    "PARSER_REJECTED_PDF_DISABLED",
    "PARSER_REJECTED_OCR_DISABLED",
    "PARSER_REJECTED_HTML_FUTURE",
    "PARSER_REJECTED_BINARY",
    "PARSER_REJECTED_PATH_ESCAPE",
    "PARSER_QUARANTINE_RECOMMENDED",
    "PARSER_FAILURE_RECORDED",
}

CLASSIFICATION_CLASSES = {
    "TEXT_PLAIN_ALLOWED",
    "MARKDOWN_ALLOWED",
    "JSON_MANIFEST_ALLOWED",
    "PDF_REJECTED_DISABLED",
    "OCR_REJECTED_DISABLED",
    "HTML_REJECTED_FUTURE",
    "BINARY_REJECTED",
    "UNKNOWN_REJECTED",
    "PATH_TRAVERSAL_REJECTED",
    "SYMLINK_REJECTED",
    "DIRECTORY_CRAWL_REJECTED",
}

ACCEPTED_CLASSIFICATION_CLASSES = {
    "TEXT_PLAIN_ALLOWED",
    "MARKDOWN_ALLOWED",
    "JSON_MANIFEST_ALLOWED",
}

RECORD_TYPES = {
    "document_intake_manifest_v1",
    "document_file_record_v1",
    "document_type_classification_v1",
    "parser_sandbox_policy_v1",
    "extraction_receipt_v1",
    "extraction_failure_record_v1",
    "parser_quarantine_record_v1",
    "document_redaction_record_v1",
    "document_source_identity_v1",
    "document_provenance_adapter_record_v1",
    "document_intake_gate_result_v1",
}

POLICY_DEFAULTS = {
    "pdf_ingestion_enabled": False,
    "ocr_enabled": False,
    "arbitrary_file_ingestion_enabled": False,
    "web_fetch_enabled": False,
    "external_provider_enabled": False,
    "parser_execution_enabled": False,
    "content_extraction_enabled": False,
    "directory_crawling_enabled": False,
    "symlink_following_enabled": False,
    "tool_authorization_enabled": False,
    "automatic_belief_promotion_enabled": False,
    "deletion_enabled": False,
}

STABLE_HASH_EXCLUDE = {
    "record_hash",
    "gate_hash",
    "manifest_hash",
    "classification_hash",
    "receipt_hash",
    "created_at",
    "base_head",
    "proof_bundle",
    "mtime",
}


class DIBBoundaryError(ValueError):
    """DIB truth, authority, or side-effect boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "document_treated_as_truth": False,
        "parsed_text_treated_as_truth": False,
        "extracted_text_treated_as_truth": False,
        "ocr_text_treated_as_truth": False,
        "metadata_treated_as_provenance": False,
        "filename_treated_as_source_identity": False,
        "parser_success_treated_as_correctness": False,
        "classification_granted_trust": False,
        "extension_treated_as_truth": False,
        "media_type_treated_as_trust": False,
        "accepted_type_is_ingestion_approval": False,
        "rejected_type_is_deletion": False,
        "extraction_is_interpretation": False,
        "quarantine_is_deletion": False,
        "redaction_is_erasure": False,
        "parser_execution_authorized": False,
        "content_extraction_authorized": False,
        "truth_claimed": False,
        "certainty_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "deletion_performed": False,
        "patch_request_applied": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ingestion_enabled": False,
        "ocr_ingestion_enabled": False,
        "directory_crawling_enabled": False,
        "symlink_following_enabled": False,
        "web_fetch_enabled": False,
        "external_provider_enabled": False,
        "parser_execution_enabled": False,
        "content_extraction_enabled": False,
        "old_proof_mutated": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k not in STABLE_HASH_EXCLUDE})


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise DIBBoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)


def with_hash(record: dict, hash_field: str = "record_hash") -> dict:
    record[hash_field] = record_hash(record)
    assert_neutral(record)
    return record
