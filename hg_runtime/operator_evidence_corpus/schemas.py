"""OEC schema foundation and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

CORPUS_APPROVED_ROOT = "tests/fixtures/operator_evidence_corpus"
ALLOWED_EXTENSIONS = (".txt", ".md")
DENIED_EXTENSIONS = (".pdf", ".bin", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".zip")

VERDICT_GREEN_OEC0 = "GREEN_OEC_0_SCHEMA_POLICY"
VERDICT_RED_OEC0 = "RED_OEC_0_SCHEMA_POLICY_FAILED"
VERDICT_GREEN_OEC1 = "GREEN_OEC_1_CURATED_TEXT_CORPUS"
VERDICT_RED_OEC1 = "RED_OEC_1_CURATED_TEXT_CORPUS_FAILED"
VERDICT_GREEN_OEC2 = "GREEN_OEC_2_CORPUS_TO_LEB_HARNESS"
VERDICT_RED_OEC2 = "RED_OEC_2_CORPUS_TO_LEB_HARNESS_FAILED"
VERDICT_GREEN_OEC3 = "GREEN_OEC_3_CORPUS_EWP_EVALUATION"
VERDICT_RED_OEC3 = "RED_OEC_3_CORPUS_EWP_EVALUATION_FAILED"
VERDICT_GREEN_OEC_CONSOLIDATION = "GREEN_OEC_OPERATOR_EVIDENCE_CORPUS_CONSOLIDATION"
VERDICT_RED_OEC_CONSOLIDATION = "RED_OEC_OPERATOR_EVIDENCE_CORPUS_CONSOLIDATION_FAILED"

CLAIM_FAMILY_IDS = {
    "TWO_INDEPENDENT_SOURCES",
    "DUPLICATE_DISGUISED_AS_SECOND",
    "CONTRADICTED_BY_SECOND",
    "STALE_VS_CURRENT",
    "QUARANTINE_RECOMMENDED",
    "INSUFFICIENT_EVIDENCE",
    "REDACTION_SENSITIVE",
    "LOW_QUALITY_PRESERVED",
    "HIGH_QUALITY_NOT_TRUTH",
    "OPERATOR_REVIEW_REQUIRED",
}

EXPECTED_OUTCOME_TYPES = {
    "TWO_INDEPENDENT_SOURCES_PRESENT",
    "DUPLICATE_NOT_CORROBORATION",
    "CONTRADICTION_VISIBLE",
    "STALE_NOT_FALSE",
    "QUARANTINE_RECOMMENDED",
    "INSUFFICIENT_EVIDENCE",
    "REDACTION_REQUIRED",
    "LOW_QUALITY_PRESERVED",
    "HIGH_QUALITY_NOT_CERTAINTY",
    "OPERATOR_REVIEW_REQUIRED",
}

RECORD_TYPES = {
    "operator_evidence_corpus_v1",
    "corpus_manifest_v1",
    "corpus_source_v1",
    "corpus_claim_v1",
    "corpus_claim_packet_v1",
    "corpus_expected_outcome_v1",
    "corpus_boundary_policy_v1",
    "corpus_gate_result_v1",
}

FORBIDDEN_FIELDS = {
    "is_true",
    "is_false",
    "certainty",
    "factually_correct",
    "permit_granted",
    "approved_by",
    "operator_approval",
    "authority_level",
    "delete_requested",
    "corpus_is_world_truth",
}


class OECBoundaryError(ValueError):
    """OEC truth, authority, or side-effect boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "corpus_treated_as_truth": False,
        "corpus_source_treated_as_authority": False,
        "fixture_corpus_treated_as_world": False,
        "expected_outcome_treated_as_proof": False,
        "expected_outcome_treated_as_truth": False,
        "packet_treated_as_truth": False,
        "second_source_result_treated_as_truth": False,
        "contradiction_record_treated_as_resolution": False,
        "dashboard_treated_as_operator_approval": False,
        "source_quality_treated_as_truth": False,
        "provenance_treated_as_authority": False,
        "duplicate_treated_as_corroboration": False,
        "stale_source_treated_as_false": False,
        "low_quality_deletion_permission": False,
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
        "directory_crawling_enabled": False,
        "links_followed": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash(
        {
            k: v
            for k, v in record.items()
            if k
            not in {
                "record_hash",
                "corpus_hash",
                "manifest_hash",
                "gate_hash",
                "packet_hash",
            }
        }
    )


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_FIELDS:
            raise OECBoundaryError(f"forbidden_field:{key}")
        if key in FORBIDDEN_TRUE and value:
            raise OECBoundaryError(f"forbidden_true:{key}")
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
