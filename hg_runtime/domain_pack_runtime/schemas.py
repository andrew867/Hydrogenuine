"""P28 domain pack runtime schema constants and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.domain_pack_runtime.hashing import stable_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_P28_0 = "GREEN_P28_0_DOMAIN_PACK_SCHEMAS"
VERDICT_RED_P28_0 = "RED_P28_0_DOMAIN_PACK_SCHEMAS_FAILED"
VERDICT_GREEN_P28_1 = "GREEN_P28_1_DOMAIN_PACK_BUILDER"
VERDICT_RED_P28_1 = "RED_P28_1_DOMAIN_PACK_BUILDER_FAILED"
VERDICT_GREEN_P28_2 = "GREEN_P28_2_DOMAIN_PACK_READINESS"
VERDICT_RED_P28_2 = "RED_P28_2_DOMAIN_PACK_READINESS_FAILED"
VERDICT_GREEN_P28_3 = "GREEN_P28_3_DOMAIN_PACK_SOAK"
VERDICT_RED_P28_3 = "RED_P28_3_DOMAIN_PACK_SOAK_FAILED"
VERDICT_GREEN_P28_CONSOLIDATION = "GREEN_P28_DOMAIN_PACK_RUNTIME_CONSOLIDATION"
VERDICT_RED_P28_CONSOLIDATION = "RED_P28_DOMAIN_PACK_RUNTIME_CONSOLIDATION_FAILED"
VERDICT_GREEN_BATCH_A = "GREEN_GENERALIST_RUNTIME_BATCH_A_P27_P28"
VERDICT_RED_BATCH_A = "RED_GENERALIST_RUNTIME_BATCH_A_P27_P28_FAILED"

VERDICT_GREEN_P27_CONSOLIDATION = "GREEN_P27_SKILL_GRAPH_TRANSFER_ENGINE_CONSOLIDATION"

SOAK_ITERATION_COUNT = 5

READINESS_STATES = frozenset({"NOT_READY", "READY_FOR_REVIEW", "REFUSED_BY_BOUNDARY"})

P28_INVARIANTS = {
    "P28-INV-01": "domain_pack_is_not_permission",
    "P28-INV-02": "domain_label_is_not_expertise",
    "P28-INV-03": "readiness_is_not_deployment_permission",
    "P28-INV-04": "skill_link_is_not_authority",
    "P28-INV-05": "explicit_manifest_only",
    "P28-INV-06": "provenance_required",
    "P28-INV-07": "no_tool_authorization",
    "P28-INV-08": "no_live_effects",
    "P28-INV-09": "phase19_yellow_preserved",
    "P28-INV-10": "phase24_infrastructure_only_preserved",
}

RECORD_TYPES = {
    "domain_pack_policy_v1",
    "domain_pack_record_v1",
    "domain_pack_skill_link_v1",
    "domain_pack_boundary_record_v1",
    "domain_pack_readiness_record_v1",
    "domain_pack_gate_result_v1",
}


class DomainPackBatchBoundaryError(ValueError):
    """P28 batch boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "domain_pack_treated_as_permission": False,
        "domain_label_treated_as_expertise": False,
        "readiness_treated_as_deployment_permission": False,
        "skill_link_treated_as_authority": False,
        "skill_treated_as_authority": False,
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
        "mutation_auto_repaired": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return stable_hash(record)


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise DomainPackBatchBoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
