"""P31 evaluation harness schema constants and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.evaluation_harness.hashing import stable_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_P31_0 = "GREEN_P31_0_EVALUATION_HARNESS_SCHEMAS"
VERDICT_RED_P31_0 = "RED_P31_0_EVALUATION_HARNESS_SCHEMAS_FAILED"
VERDICT_GREEN_P31_1 = "GREEN_P31_1_TASK_FAMILY_FIXTURE_RUNNER"
VERDICT_RED_P31_1 = "RED_P31_1_TASK_FAMILY_FIXTURE_RUNNER_FAILED"
VERDICT_GREEN_P31_2 = "GREEN_P31_2_COMPETENCE_REFUSAL_RECEIPTS"
VERDICT_RED_P31_2 = "RED_P31_2_COMPETENCE_REFUSAL_RECEIPTS_FAILED"
VERDICT_GREEN_P31_3 = "GREEN_P31_3_EVALUATION_HARNESS_SOAK"
VERDICT_RED_P31_3 = "RED_P31_3_EVALUATION_HARNESS_SOAK_FAILED"
VERDICT_GREEN_P31_CONSOLIDATION = "GREEN_P31_EVALUATION_HARNESS_CONSOLIDATION"
VERDICT_RED_P31_CONSOLIDATION = "RED_P31_EVALUATION_HARNESS_CONSOLIDATION_FAILED"

SOAK_ITERATION_COUNT = 5

RECORD_TYPES = {
    "evaluation_policy_v1",
    "task_family_v1",
    "evaluation_fixture_v1",
    "expected_observed_record_v1",
    "evaluation_result_v1",
    "competence_claim_refusal_v1",
    "evaluation_harness_gate_result_v1",
}

TASK_FAMILIES = frozenset({
    "code_generation",
    "summarization",
    "classification",
    "boundary_enforcement",
    "gate_output",
    "consolidation_doc",
})

EVALUATION_RESULT_STATES = frozenset({
    "PASS",
    "FAIL",
    "DEFER",
    "REFUSE",
})

COMPETENCE_CLAIM_TYPES = frozenset({
    "evaluation_pass_treated_as_truth",
    "benchmark_score_treated_as_competence",
    "task_family_treated_as_general_competence",
    "benchmark_treated_as_deployment_permission",
    "fixture_pass_treated_as_real_world_readiness",
    "model_route_treated_as_authority",
    "tool_authorization_requested",
    "live_provider_web_requested",
})

P31_INVARIANTS = {
    "P31-INV-01": "evaluation_pass_is_not_truth",
    "P31-INV-02": "evaluation_score_is_not_competence",
    "P31-INV-03": "benchmark_is_not_deployment_permission",
    "P31-INV-04": "expected_observed_match_is_not_truth",
    "P31-INV-05": "task_family_is_not_general_competence",
    "P31-INV-06": "no_tool_authorization",
    "P31-INV-07": "no_live_effects",
    "P31-INV-08": "no_web_provider",
    "P31-INV-09": "no_pdf_ocr_html",
    "P31-INV-10": "no_automatic_belief_promotion",
    "P31-INV-11": "phase19_yellow_preserved",
    "P31-INV-12": "phase24_infrastructure_only_preserved",
}


def neutral_flags() -> dict[str, bool]:
    return {
        "evaluation_treated_as_truth": False,
        "evaluation_treated_as_competence": False,
        "benchmark_treated_as_deployment_permission": False,
        "competence_claimed": False,
        "tool_authorization_granted": False,
        "tools_authorized": False,
        "authority_granted": False,
        "belief_promotion_automatic": False,
        "live_external_side_effects_created": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "patch_request_applied": False,
        "deletion_performed": False,
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


class EvaluationHarnessBoundaryError(ValueError):
    """P31 boundary violation."""


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise EvaluationHarnessBoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
