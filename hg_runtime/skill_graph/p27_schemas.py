"""P27 batch skill graph schema constants and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.skill_graph.hashing import stable_hash

VERDICT_GREEN_P26_CONSOLIDATION = "GREEN_P26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER_CONSOLIDATION"

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_P27_0 = "GREEN_P27_0_SKILL_GRAPH_SCHEMAS"
VERDICT_RED_P27_0 = "RED_P27_0_SKILL_GRAPH_SCHEMAS_FAILED"
VERDICT_GREEN_P27_1 = "GREEN_P27_1_SKILL_EXTRACTION"
VERDICT_RED_P27_1 = "RED_P27_1_SKILL_EXTRACTION_FAILED"
VERDICT_GREEN_P27_2 = "GREEN_P27_2_SKILL_GRAPH_TRANSFER_CANDIDATES"
VERDICT_RED_P27_2 = "RED_P27_2_SKILL_GRAPH_TRANSFER_CANDIDATES_FAILED"
VERDICT_GREEN_P27_3 = "GREEN_P27_3_SKILL_GRAPH_SOAK"
VERDICT_RED_P27_3 = "RED_P27_3_SKILL_GRAPH_SOAK_FAILED"
VERDICT_GREEN_P27_CONSOLIDATION = "GREEN_P27_SKILL_GRAPH_TRANSFER_ENGINE_CONSOLIDATION"
VERDICT_RED_P27_CONSOLIDATION = "RED_P27_SKILL_GRAPH_TRANSFER_ENGINE_CONSOLIDATION_FAILED"

SOAK_ITERATION_COUNT = 5

P27_INVARIANTS = {
    "P27-INV-01": "skill_is_not_authority",
    "P27-INV-02": "skill_reuse_is_not_transfer_proof",
    "P27-INV-03": "transfer_candidate_is_not_competence",
    "P27-INV-04": "memory_source_required",
    "P27-INV-05": "provenance_required",
    "P27-INV-06": "no_tool_authorization",
    "P27-INV-07": "no_live_effects",
    "P27-INV-08": "no_automatic_belief_promotion",
    "P27-INV-09": "phase19_yellow_preserved",
    "P27-INV-10": "phase24_infrastructure_only_preserved",
}

RECORD_TYPES = {
    "skill_graph_policy_v1",
    "skill_record_v1",
    "skill_edge_v1",
    "skill_source_memory_link_v1",
    "transfer_candidate_v1",
    "transfer_result_v1",
    "skill_graph_gate_result_v1",
}


class SkillGraphBatchBoundaryError(ValueError):
    """P27 batch boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "skill_treated_as_authority": False,
        "skill_reuse_treated_as_transfer_proof": False,
        "transfer_candidate_treated_as_competence": False,
        "transfer_treated_as_proof": False,
        "memory_treated_as_truth": False,
        "recall_treated_as_authority": False,
        "truth_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "tool_authorization_granted": False,
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
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return stable_hash(record)


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise SkillGraphBatchBoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
