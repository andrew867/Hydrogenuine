"""SQP schema foundation and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_SQP0 = "GREEN_SQP_0_SCHEMA_FOUNDATION"
VERDICT_RED_SQP0 = "RED_SQP_0_SCHEMA_FOUNDATION_FAILED"
VERDICT_GREEN_SQP1 = "GREEN_SQP_1_FINGERPRINT_DUPLICATE_DETECTOR"
VERDICT_RED_SQP1 = "RED_SQP_1_FINGERPRINT_DUPLICATE_DETECTOR_FAILED"
VERDICT_GREEN_SQP2 = "GREEN_SQP_2_SOURCE_QUALITY_SCORER"
VERDICT_RED_SQP2 = "RED_SQP_2_SOURCE_QUALITY_SCORER_FAILED"
VERDICT_GREEN_SQP3 = "GREEN_SQP_3_PROVENANCE_GRAPH"
VERDICT_RED_SQP3 = "RED_SQP_3_PROVENANCE_GRAPH_FAILED"
VERDICT_GREEN_SQP4 = "GREEN_SQP_4_STALENESS_CONFLICT_DETECTOR"
VERDICT_RED_SQP4 = "RED_SQP_4_STALENESS_CONFLICT_DETECTOR_FAILED"
VERDICT_GREEN_SQP5 = "GREEN_SQP_5_REVIEW_POLICY_ADAPTER"
VERDICT_RED_SQP5 = "RED_SQP_5_REVIEW_POLICY_ADAPTER_FAILED"
VERDICT_GREEN_SQP_CONSOLIDATION = "GREEN_SQP_SOURCE_QUALITY_PROVENANCE_CONSOLIDATION"
VERDICT_RED_SQP_CONSOLIDATION = "RED_SQP_SOURCE_QUALITY_PROVENANCE_CONSOLIDATION_FAILED"

PROVENANCE_NODE_TYPES = {
    "SOURCE",
    "EXCERPT",
    "EVIDENCE_RECEIPT",
    "CLAIM_LINK",
    "REVIEW_DECISION",
    "PROMOTION_REQUEST",
    "REVISION_INPUT",
    "REVIEWED_BELIEF_STATE",
    "FINGERPRINT",
    "QUALITY_SCORE",
}

PROVENANCE_EDGE_TYPES = {
    "DERIVED_FROM",
    "EXCERPTED_FROM",
    "LINKS_TO_CLAIM",
    "REVIEWED_BY",
    "REQUESTED_PROMOTION_FROM",
    "GATED_INTO",
    "PRODUCED_BELIEF_STATE",
    "HAS_FINGERPRINT",
    "HAS_QUALITY_SCORE",
    "DUPLICATE_OF",
}

STALENESS_CLASSES = {
    "CURRENT_ENOUGH",
    "DATE_UNKNOWN",
    "POSSIBLY_STALE",
    "STALE_BY_POLICY",
    "SUPERSEDED_BY_REVIEWED_SOURCE",
    "RETRACTED_OR_QUARANTINED",
}

CONFLICT_CLASSES = {
    "CLAIM_CONFLICT",
    "SOURCE_METADATA_CONFLICT",
    "QUALITY_CONFLICT",
    "REVIEW_DECISION_CONFLICT",
    "DUPLICATE_INDEPENDENCE_CONFLICT",
    "RETRACTION_CONFLICT",
}

REVIEW_HINT_TYPES = {
    "PRIORITIZE_REVIEW",
    "REQUEST_MORE_EVIDENCE",
    "REQUIRE_SECOND_SOURCE",
    "REQUIRE_OPERATOR_CONFIRMATION",
    "QUARANTINE_RECOMMENDED",
    "RETRACTION_RECOMMENDED",
    "BLOCK_PROMOTION_REQUEST",
    "ALLOW_PROVISIONAL_REVIEW",
}

REVIEW_PRIORITY_BANDS = {
    "LOW",
    "NORMAL",
    "HIGH",
    "CRITICAL_REVIEW_REQUIRED",
}

DUPLICATE_CLASSES = {
    "EXACT_CONTENT_DUPLICATE",
    "NORMALIZED_TEXT_DUPLICATE",
    "SAME_SOURCE_DIFFERENT_EXCERPT",
    "SAME_TEXT_DIFFERENT_PATH",
    "SUSPECT_COPY_WITHOUT_INDEPENDENCE",
    "NOT_DUPLICATE",
}

QUALITY_FEATURE_CATEGORIES = {
    "HAS_SOURCE_IDENTITY",
    "HAS_STABLE_FINGERPRINT",
    "HAS_EXCERPT_BOUNDARY",
    "HAS_REDACTION_STATUS",
    "HAS_REVIEW_DECISION",
    "HAS_PROVENANCE_LINK",
    "DUPLICATE_COLLAPSED",
    "STALE_SIGNAL_PRESENT",
    "CONFLICT_SIGNAL_PRESENT",
    "QUARANTINE_HISTORY_PRESENT",
    "SECURITY_FINDING_PRESENT",
}

QUALITY_BANDS = {
    "UNRATED",
    "LOW_INFORMATION",
    "STRUCTURALLY_USABLE",
    "REVIEWED_USABLE",
    "CONFLICTED_OR_QUARANTINED",
    "BLOCKED",
}

RECORD_TYPES = {
    "source_identity_v1",
    "source_fingerprint_v1",
    "duplicate_source_record_v1",
    "source_quality_score_v1",
    "provenance_node_v1",
    "provenance_edge_v1",
    "provenance_graph_v1",
    "source_staleness_record_v1",
    "source_conflict_record_v1",
    "source_redaction_status_v1",
    "source_quarantine_history_v1",
    "source_review_policy_hint_v1",
    "provenance_graph_manifest_v1",
    "conflict_cluster_v1",
    "review_priority_record_v1",
    "blocked_review_hint_v1",
    "sqp_gate_result_v1",
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


class SQPBoundaryError(ValueError):
    """SQP truth, authority, or side-effect boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
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
                "identity_hash",
                "fingerprint_hash",
                "quality_hash",
                "graph_hash",
                "manifest_hash",
                "gate_hash",
            }
        }
    )


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_FIELDS:
            raise SQPBoundaryError(f"forbidden_field:{key}")
        if key in FORBIDDEN_TRUE and value:
            raise SQPBoundaryError(f"forbidden_true:{key}")
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
