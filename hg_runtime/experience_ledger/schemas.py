"""P26 experience ledger schema constants and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.experience_ledger.hashing import stable_hash

PHASE_ID_P26_0 = "P26-0"
PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_P26_0 = "GREEN_P26_0_EXPERIENCE_LEDGER_SCHEMAS"
VERDICT_RED_P26_0 = "RED_P26_0_EXPERIENCE_LEDGER_SCHEMAS_FAILED"
VERDICT_GREEN_P26_1 = "GREEN_P26_1_EXPERIENCE_LEDGER_ADAPTER"
VERDICT_RED_P26_1 = "RED_P26_1_EXPERIENCE_LEDGER_ADAPTER_FAILED"
VERDICT_GREEN_P26_2 = "GREEN_P26_2_READ_ONLY_RECALL_SURFACE"
VERDICT_RED_P26_2 = "RED_P26_2_READ_ONLY_RECALL_SURFACE_FAILED"
VERDICT_GREEN_P26_3 = "GREEN_P26_3_ORP_GATED_MEMORY_PROMOTION_BRIDGE"
VERDICT_RED_P26_3 = "RED_P26_3_ORP_GATED_MEMORY_PROMOTION_BRIDGE_FAILED"
VERDICT_GREEN_P26_4 = "GREEN_P26_4_RECALL_REPLAY_SOAK"
VERDICT_RED_P26_4 = "RED_P26_4_RECALL_REPLAY_SOAK_FAILED"
VERDICT_GREEN_P26_CONSOLIDATION = "GREEN_P26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER_CONSOLIDATION"
VERDICT_RED_P26_CONSOLIDATION = "RED_P26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER_CONSOLIDATION_FAILED"

RECALL_QUERY_TYPES = {
    "by_family",
    "by_verdict",
    "by_boundary_tag",
    "by_artifact_id",
    "by_time_window",
    "by_risk_tag",
    "by_retraction_status",
    "by_quarantine_status",
}

RECORD_TYPES = {
    "experience_ledger_policy_v1",
    "experience_record_v1",
    "memory_record_v1",
    "recall_query_v1",
    "recall_result_v1",
    "memory_promotion_request_v1",
    "memory_promotion_decision_v1",
    "memory_retraction_record_v1",
    "experience_ledger_gate_result_v1",
}

P26_INVARIANTS = {
    "P26-INV-01": "memory_is_not_truth",
    "P26-INV-02": "recall_is_not_authority",
    "P26-INV-03": "experience_is_not_evidence_by_itself",
    "P26-INV-04": "ledger_entry_is_not_belief",
    "P26-INV-05": "promotion_request_is_not_promotion",
    "P26-INV-06": "operator_review_is_not_truth",
    "P26-INV-07": "provenance_required_for_recall",
    "P26-INV-08": "source_quality_is_not_truth",
    "P26-INV-09": "retraction_is_not_erasure",
    "P26-INV-10": "quarantine_is_not_deletion",
    "P26-INV-11": "no_automatic_belief_promotion",
    "P26-INV-12": "no_tool_authorization",
    "P26-INV-13": "no_live_effects",
    "P26-INV-14": "phase19_yellow_preserved",
    "P26-INV-15": "phase24_infrastructure_only_preserved",
}

REQUIRED_POLICY_DEFAULTS = {
    "memory_treated_as_truth": False,
    "recall_treated_as_authority": False,
    "experience_treated_as_evidence_by_itself": False,
    "automatic_belief_promotion_enabled": False,
    "operator_promotion_required": True,
    "orp_bridge_required": True,
    "provenance_required": True,
    "hash_chain_required": True,
    "retraction_supported": True,
    "quarantine_supported": True,
    "deletion_enabled": False,
    "live_effects_enabled": False,
    "external_provider_enabled": False,
    "web_enabled": False,
    "pdf_ocr_enabled": False,
    "tool_authorization_enabled": False,
}


def neutral_flags() -> dict[str, bool]:
    return {
        "memory_treated_as_truth": False,
        "recall_treated_as_authority": False,
        "experience_treated_as_evidence_by_itself": False,
        "ledger_entry_treated_as_belief": False,
        "promotion_request_is_promotion": False,
        "operator_review_treated_as_truth": False,
        "source_quality_treated_as_truth": False,
        "provenance_treated_as_authority": False,
        "truth_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "tool_authorization_granted": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "promotion_request_auto_applied": False,
        "orp_bypassed": False,
        "deletion_performed": False,
        "patch_request_applied": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ingestion_enabled": False,
        "ocr_enabled": False,
        "html_parsing_enabled": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


class ExperienceLedgerBoundaryError(ValueError):
    """P26 memory, recall, authority, or side-effect boundary violation."""


def record_hash(record: Mapping[str, Any]) -> str:
    return stable_hash(record)


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise ExperienceLedgerBoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
