"""DTX schema foundation and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

DTX_APPROVED_ROOT = "tests/fixtures/document_text_exchange"
ALLOWED_EXTENSIONS = (".txt", ".md")
DENIED_EXTENSIONS = (".pdf", ".bin", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".html", ".htm")

VERDICT_GREEN_DTX0 = "GREEN_DTX_0_SCHEMA_POLICY"
VERDICT_RED_DTX0 = "RED_DTX_0_SCHEMA_POLICY_FAILED"
VERDICT_GREEN_DTX1 = "GREEN_DTX_1_SAFE_TEXT_DOCUMENT_CORPUS"
VERDICT_RED_DTX1 = "RED_DTX_1_SAFE_TEXT_DOCUMENT_CORPUS_FAILED"
VERDICT_GREEN_DTX2 = "GREEN_DTX_2_DIB_TO_LEB_BRIDGE"
VERDICT_RED_DTX2 = "RED_DTX_2_DIB_TO_LEB_BRIDGE_FAILED"
VERDICT_GREEN_DTX3 = "GREEN_DTX_3_DOCUMENT_PACKET_EVALUATION"
VERDICT_RED_DTX3 = "RED_DTX_3_DOCUMENT_PACKET_EVALUATION_FAILED"
VERDICT_GREEN_DTX4 = "GREEN_DTX_4_DOCUMENT_TEXT_SOAK"
VERDICT_RED_DTX4 = "RED_DTX_4_DOCUMENT_TEXT_SOAK_FAILED"
VERDICT_GREEN_DTX_CONSOLIDATION = "GREEN_DTX_SAFE_TEXT_DOCUMENT_EXCHANGE_CONSOLIDATION"
VERDICT_RED_DTX_CONSOLIDATION = "RED_DTX_SAFE_TEXT_DOCUMENT_EXCHANGE_CONSOLIDATION_FAILED"

SOAK_ITERATION_COUNT = 5

DOCUMENT_FIXTURE_FAMILIES = {
    "PLAIN_TEXT_SUPPORT",
    "MARKDOWN_SUPPORT",
    "DUPLICATE_MARKDOWN_COPY",
    "CONTRADICTORY_TEXT",
    "STALE_TEXT",
    "REDACTION_SENSITIVE",
    "LOW_QUALITY_PRESERVED",
    "HIGH_QUALITY_NOT_TRUTH",
    "EXTRACTION_FAILURE_CANDIDATE",
    "SOURCE_IDENTITY_NOT_FILENAME",
}

EXPECTED_OUTCOME_TYPES = {
    "PLAIN_TEXT_EXCHANGE_RECORDED",
    "MARKDOWN_EXCHANGE_RECORDED",
    "DUPLICATE_NOT_CORROBORATION",
    "CONTRADICTION_VISIBLE",
    "STALE_NOT_FALSE",
    "REDACTION_REQUIRED",
    "LOW_QUALITY_PRESERVED",
    "HIGH_QUALITY_NOT_TRUTH",
    "EXTRACTION_FAILURE_RECORDED",
    "SOURCE_IDENTITY_NOT_FILENAME",
}

MUTATION_PROBE_TYPES = {
    "MODIFIED_EXTRACTION_RECEIPT_HASH",
    "MODIFIED_PACKET_SUPPORT_RECORD",
    "MODIFIED_DASHBOARD_SUMMARY",
    "MODIFIED_SECOND_SOURCE_RESULT",
    "MODIFIED_CONTRADICTION_PACKET",
}

RECORD_TYPES = {
    "safe_text_document_exchange_v1",
    "dtx_manifest_v1",
    "dtx_document_fixture_v1",
    "dtx_extraction_exchange_record_v1",
    "dtx_leb_bridge_record_v1",
    "dtx_packet_exchange_record_v1",
    "dtx_soak_iteration_v1",
    "dtx_gate_result_v1",
    "dtx_boundary_policy_v1",
    "dtx_expected_outcome_v1",
}

STABLE_HASH_EXCLUDE = {
    "record_hash",
    "gate_hash",
    "manifest_hash",
    "exchange_hash",
    "packet_hash",
    "dashboard_hash",
    "receipt_hash",
    "content_hash",
    "created_at",
    "base_head",
    "proof_bundle",
    "iteration_started_at",
    "iteration_completed_at",
}


class DTXBoundaryError(ValueError):
    """DTX truth, authority, or side-effect boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "document_exchange_treated_as_truth": False,
        "document_corpus_treated_as_world": False,
        "extracted_text_treated_as_truth": False,
        "parsed_text_treated_as_truth": False,
        "dib_adapter_treated_as_belief_promotion": False,
        "leb_receipt_treated_as_truth": False,
        "expected_outcome_treated_as_proof": False,
        "packet_treated_as_truth": False,
        "second_source_result_treated_as_truth": False,
        "contradiction_record_treated_as_resolution": False,
        "dashboard_treated_as_operator_approval": False,
        "replay_match_treated_as_truth": False,
        "soak_treated_as_truth": False,
        "mutation_detection_is_repair": False,
        "mutation_auto_repaired": False,
        "content_hash_treated_as_truth": False,
        "filename_treated_as_source_identity": False,
        "metadata_treated_as_provenance": False,
        "parser_success_treated_as_correctness": False,
        "duplicate_treated_as_corroboration": False,
        "stale_source_treated_as_false": False,
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
        "html_parsing_enabled": False,
        "directory_crawling_enabled": False,
        "symlink_following_enabled": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k not in STABLE_HASH_EXCLUDE})


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise DTXBoundaryError(f"forbidden_true:{key}")
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
