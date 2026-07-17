"""SLE-RC schema foundation and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

COMPONENT_FAMILIES = (
    "WMBR",
    "AIS",
    "LEB",
    "ORP",
    "SQP",
    "EWP",
    "OEC",
    "OES",
    "DIB",
    "DTX",
)

COMPONENT_CONSOLIDATION = {
    "WMBR": ("WMBR-TRANCHE-CONSOLIDATION", "GREEN_WMBR_TRANCHE_CONSOLIDATION_HANDOFF"),
    "AIS": ("SAFE-LOCAL-EVIDENCE-ALPHA", "GREEN_SAFE_LOCAL_EVIDENCE_ALPHA"),
    "LEB": ("LEB-LOCAL-EVIDENCE-BRIDGE-CONSOLIDATION", "GREEN_LEB_LOCAL_EVIDENCE_BRIDGE_CONSOLIDATION"),
    "ORP": ("REVIEWED-LOCAL-EVIDENCE-BETA", "GREEN_REVIEWED_LOCAL_EVIDENCE_BETA"),
    "SQP": ("SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION", "GREEN_SQP_SOURCE_QUALITY_PROVENANCE_CONSOLIDATION"),
    "EWP": ("EWP-EVIDENCE-WORKBENCH-PACKET-CONSOLIDATION", "GREEN_EWP_EVIDENCE_WORKBENCH_PACKET_CONSOLIDATION"),
    "OEC": ("OEC-OPERATOR-EVIDENCE-CORPUS-CONSOLIDATION", "GREEN_OEC_OPERATOR_EVIDENCE_CORPUS_CONSOLIDATION"),
    "OES": ("OES-OPERATOR-EVIDENCE-SOAK-CONSOLIDATION", "GREEN_OES_OPERATOR_EVIDENCE_SOAK_CONSOLIDATION"),
    "DIB": ("DIB-DOCUMENT-INTAKE-BOUNDARY-CONSOLIDATION", "GREEN_DIB_DOCUMENT_INTAKE_BOUNDARY_CONSOLIDATION"),
    "DTX": ("DTX-SAFE-TEXT-DOCUMENT-EXCHANGE-CONSOLIDATION", "GREEN_DTX_SAFE_TEXT_DOCUMENT_EXCHANGE_CONSOLIDATION"),
}

VERDICT_GREEN_SLE_RC0 = "GREEN_SLE_RC_0_SCHEMA_MANIFEST"
VERDICT_RED_SLE_RC0 = "RED_SLE_RC_0_SCHEMA_MANIFEST_FAILED"
VERDICT_GREEN_SLE_RC1 = "GREEN_SLE_RC_1_ARTIFACT_INDEX_STATUS"
VERDICT_RED_SLE_RC1 = "RED_SLE_RC_1_ARTIFACT_INDEX_STATUS_FAILED"
VERDICT_GREEN_SLE_RC2 = "GREEN_SLE_RC_2_BOUNDARY_MATRIX"
VERDICT_RED_SLE_RC2 = "RED_SLE_RC_2_BOUNDARY_MATRIX_FAILED"
VERDICT_GREEN_SLE_RC3 = "GREEN_SLE_RC_3_END_TO_END_SOAK"
VERDICT_RED_SLE_RC3 = "RED_SLE_RC_3_END_TO_END_SOAK_FAILED"
VERDICT_GREEN_SLE_RC_CONSOLIDATION = "GREEN_SLE_SAFE_LOCAL_EVIDENCE_RELEASE_CANDIDATE"
VERDICT_RED_SLE_RC_CONSOLIDATION = "RED_SLE_SAFE_LOCAL_EVIDENCE_RELEASE_CANDIDATE_FAILED"
VERDICT_GREEN_SLE_RC_EXTENDED = "GREEN_SLE_RC_EXTENDED_REGRESSION_SOAK"
VERDICT_RED_SLE_RC_EXTENDED = "RED_SLE_RC_EXTENDED_REGRESSION_SOAK_FAILED"

RC_SOAK_ITERATION_COUNT = 3

BOUNDARY_ASSERTION_IDS = (
    "no_live_effects",
    "no_external_provider_calls",
    "no_web_browse",
    "no_hg_local_touch",
    "no_arbitrary_ingestion",
    "no_pdf_ingestion",
    "no_ocr",
    "no_html",
    "no_tool_authorization",
    "no_authority_grants",
    "no_belief_promotion_automatic",
    "no_deletion",
    "no_patch_application",
    "evidence_not_truth",
    "document_not_truth",
    "extracted_text_not_truth",
    "source_quality_not_truth",
    "provenance_not_authority",
    "second_source_not_truth",
    "contradiction_not_resolution",
    "dashboard_not_approval",
    "replay_match_not_truth",
    "mutation_not_auto_repaired",
    "phase19_yellow_preserved",
    "phase24_infrastructure_only_preserved",
)

RECORD_TYPES = {
    "safe_local_evidence_rc_v1",
    "rc_manifest_v1",
    "rc_component_status_v1",
    "rc_boundary_assertion_v1",
    "rc_artifact_index_v1",
    "rc_release_risk_record_v1",
    "rc_gate_result_v1",
    "rc_soak_iteration_v1",
    "rc_boundary_matrix_v1",
}

STABLE_HASH_EXCLUDE = {
    "record_hash",
    "gate_hash",
    "manifest_hash",
    "created_at",
    "base_head",
    "proof_bundle",
    "iteration_started_at",
    "iteration_completed_at",
    "receipt_hash",
    "content_hash",
}


class SLErcBoundaryError(ValueError):
    """SLE-RC truth, authority, or side-effect boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "release_candidate_is_deployment": False,
        "rc_green_is_truth": False,
        "rc_green_is_authority": False,
        "rc_green_is_live_permission": False,
        "evidence_treated_as_truth": False,
        "document_treated_as_truth": False,
        "extracted_text_treated_as_truth": False,
        "source_quality_treated_as_truth": False,
        "provenance_treated_as_authority": False,
        "second_source_treated_as_truth": False,
        "contradiction_treated_as_resolution": False,
        "dashboard_treated_as_approval": False,
        "replay_match_treated_as_truth": False,
        "soak_treated_as_truth": False,
        "stable_hash_treated_as_correctness": False,
        "mutation_detection_is_repair": False,
        "mutation_auto_repaired": False,
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
            raise SLErcBoundaryError(f"forbidden_true:{key}")
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
