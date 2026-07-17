"""EWP schema foundation and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_EWP0 = "GREEN_EWP_0_SCHEMA_FOUNDATION"
VERDICT_RED_EWP0 = "RED_EWP_0_SCHEMA_FOUNDATION_FAILED"
VERDICT_GREEN_EWP1 = "GREEN_EWP_1_CLAIM_PACKET_BUILDER"
VERDICT_RED_EWP1 = "RED_EWP_1_CLAIM_PACKET_BUILDER_FAILED"
VERDICT_GREEN_EWP2 = "GREEN_EWP_2_SECOND_SOURCE_GATE"
VERDICT_RED_EWP2 = "RED_EWP_2_SECOND_SOURCE_GATE_FAILED"
VERDICT_GREEN_EWP3 = "GREEN_EWP_3_CONTRADICTION_REVIEW_PACKETS"
VERDICT_RED_EWP3 = "RED_EWP_3_CONTRADICTION_REVIEW_PACKETS_FAILED"
VERDICT_GREEN_EWP4 = "GREEN_EWP_4_OPERATOR_PACKET_DASHBOARD"
VERDICT_RED_EWP4 = "RED_EWP_4_OPERATOR_PACKET_DASHBOARD_FAILED"
VERDICT_GREEN_EWP_CONSOLIDATION = "GREEN_EWP_EVIDENCE_WORKBENCH_PACKET_CONSOLIDATION"
VERDICT_RED_EWP_CONSOLIDATION = "RED_EWP_EVIDENCE_WORKBENCH_PACKET_CONSOLIDATION_FAILED"

PACKET_REVIEW_STATUSES = {
    "PENDING_REVIEW",
    "REVIEW_READY",
    "BLOCKED_BY_CONFLICT",
    "BLOCKED_BY_QUARANTINE",
    "BLOCKED_BY_FEVER",
    "BLOCKED_BY_REDACTION",
    "SECOND_SOURCE_REQUIRED",
}

SECOND_SOURCE_OUTCOMES = {
    "SECOND_SOURCE_NOT_REQUIRED",
    "SECOND_SOURCE_REQUIRED_MISSING",
    "SECOND_SOURCE_PRESENT_BUT_DUPLICATE",
    "SECOND_SOURCE_PRESENT_BUT_NOT_INDEPENDENT",
    "SECOND_SOURCE_PRESENT_REVIEW_READY",
    "BLOCKED_BY_CONFLICT",
    "BLOCKED_BY_QUARANTINE",
    "BLOCKED_BY_FEVER",
    "BLOCKED_BY_REDACTION",
}

RECORD_TYPES = {
    "evidence_workbench_packet_v1",
    "claim_evidence_packet_v1",
    "packet_source_summary_v1",
    "packet_support_record_v1",
    "packet_contradiction_record_v1",
    "packet_second_source_requirement_v1",
    "packet_second_source_result_v1",
    "contradiction_review_packet_v1",
    "operator_packet_dashboard_v1",
    "packet_review_status_v1",
    "packet_gate_result_v1",
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
    "corroboration_count_from_copies",
}


class EWPBoundaryError(ValueError):
    """EWP truth, authority, or side-effect boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "packet_treated_as_truth": False,
        "packet_treated_as_authority": False,
        "packet_treated_as_approval": False,
        "support_record_treated_as_proof": False,
        "contradiction_record_treated_as_resolution": False,
        "second_source_result_treated_as_truth": False,
        "dashboard_treated_as_operator_approval": False,
        "source_quality_treated_as_truth": False,
        "provenance_treated_as_authority": False,
        "duplicate_treated_as_corroboration": False,
        "many_copies_treated_as_many_sources": False,
        "stale_source_treated_as_false": False,
        "low_quality_deletion_permission": False,
        "review_hint_treated_as_operator_approval": False,
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
                "packet_hash",
                "manifest_hash",
                "gate_hash",
                "dashboard_hash",
            }
        }
    )


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_FIELDS:
            raise EWPBoundaryError(f"forbidden_field:{key}")
        if key in FORBIDDEN_TRUE and value:
            raise EWPBoundaryError(f"forbidden_true:{key}")
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
