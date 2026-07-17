"""P30 knowledge acquisition loop schema constants and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.knowledge_acquisition_loop.hashing import stable_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_P30_0 = "GREEN_P30_0_KNOWLEDGE_ACQUISITION_SCHEMAS"
VERDICT_RED_P30_0 = "RED_P30_0_KNOWLEDGE_ACQUISITION_SCHEMAS_FAILED"
VERDICT_GREEN_P30_1 = "GREEN_P30_1_ACQUISITION_TASK_BUILDER"
VERDICT_RED_P30_1 = "RED_P30_1_ACQUISITION_TASK_BUILDER_FAILED"
VERDICT_GREEN_P30_2 = "GREEN_P30_2_FIXTURE_ACQUISITION_LOOP"
VERDICT_RED_P30_2 = "RED_P30_2_FIXTURE_ACQUISITION_LOOP_FAILED"
VERDICT_GREEN_P30_3 = "GREEN_P30_3_KNOWLEDGE_ACQUISITION_SOAK"
VERDICT_RED_P30_3 = "RED_P30_3_KNOWLEDGE_ACQUISITION_SOAK_FAILED"
VERDICT_GREEN_P30_CONSOLIDATION = "GREEN_P30_KNOWLEDGE_ACQUISITION_LOOP_CONSOLIDATION"
VERDICT_RED_P30_CONSOLIDATION = "RED_P30_KNOWLEDGE_ACQUISITION_LOOP_CONSOLIDATION_FAILED"

SOAK_ITERATION_COUNT = 5

ACQUISITION_TASK_TYPES = frozenset({
    "read_local_artifact",
    "read_local_evidence",
    "read_local_proof",
    "read_local_report",
    "web_search",
    "external_provider",
    "arbitrary_directory",
    "pdf_ocr",
})

ACQUISITION_RESULT_STATES = frozenset({
    "ACQUIRED_FIXTURE",
    "ACQUIRED_LOCAL",
    "REFUSED_BY_POLICY",
    "NORMALIZED_TO_TBD",
})

REFUSAL_REASONS = frozenset({
    "live_web_acquisition",
    "external_provider_acquisition",
    "arbitrary_directory_acquisition",
    "pdf_ocr_acquisition",
    "unsourced_claim_promoted",
    "acquisition_grants_authority",
    "acquisition_task_attempts_action",
    "patch_deletion_request",
})

RECORD_TYPES = {
    "knowledge_acquisition_policy_v1",
    "acquisition_candidate_v1",
    "acquisition_task_v1",
    "acquisition_source_record_v1",
    "acquisition_result_v1",
    "acquisition_gap_record_v1",
    "knowledge_acquisition_gate_result_v1",
}

P30_INVARIANTS = {
    "P30-INV-01": "acquired_claim_is_not_truth",
    "P30-INV-02": "acquisition_result_is_not_belief",
    "P30-INV-03": "source_is_not_authority",
    "P30-INV-04": "source_quality_is_not_truth",
    "P30-INV-05": "provenance_is_not_authority",
    "P30-INV-06": "acquisition_task_is_not_action",
    "P30-INV-07": "no_live_web",
    "P30-INV-08": "no_external_provider",
    "P30-INV-09": "no_arbitrary_ingestion",
    "P30-INV-10": "no_auto_belief_promotion",
    "P30-INV-11": "phase19_yellow_preserved",
    "P30-INV-12": "phase24_infrastructure_only_preserved",
}


def neutral_flags() -> dict[str, bool]:
    return {
        "acquired_claim_treated_as_truth": False,
        "acquisition_result_treated_as_belief": False,
        "source_treated_as_authority": False,
        "source_quality_treated_as_truth": False,
        "provenance_treated_as_authority": False,
        "acquisition_task_treated_as_action": False,
        "tool_plan_treated_as_permission": False,
        "tool_request_executed_live": False,
        "tool_authorization_granted": False,
        "tools_authorized": False,
        "authority_granted": False,
        "truth_claimed": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "deletion_performed": False,
        "patch_request_applied": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ingestion_enabled": False,
        "ocr_enabled": False,
        "html_parsing_enabled": False,
        "secrets_emitted": False,
        "mutation_auto_repaired": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return stable_hash(record)


class KnowledgeAcquisitionBoundaryError(ValueError):
    """P30 boundary violation."""


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise KnowledgeAcquisitionBoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
