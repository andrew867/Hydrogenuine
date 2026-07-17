"""P29 tool-mediated workbench schema constants and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.tool_mediated_workbench.hashing import stable_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_P29_0 = "GREEN_P29_0_TOOL_WORKBENCH_SCHEMAS"
VERDICT_RED_P29_0 = "RED_P29_0_TOOL_WORKBENCH_SCHEMAS_FAILED"
VERDICT_GREEN_P29_1 = "GREEN_P29_1_TOOL_PLAN_BUILDER"
VERDICT_RED_P29_1 = "RED_P29_1_TOOL_PLAN_BUILDER_FAILED"
VERDICT_GREEN_P29_2 = "GREEN_P29_2_SANDBOXED_WORKBENCH_DRY_RUN"
VERDICT_RED_P29_2 = "RED_P29_2_SANDBOXED_WORKBENCH_DRY_RUN_FAILED"
VERDICT_GREEN_P29_3 = "GREEN_P29_3_TOOL_WORKBENCH_SOAK"
VERDICT_RED_P29_3 = "RED_P29_3_TOOL_WORKBENCH_SOAK_FAILED"
VERDICT_GREEN_P29_CONSOLIDATION = "GREEN_P29_TOOL_MEDIATED_WORKBENCH_CONSOLIDATION"
VERDICT_RED_P29_CONSOLIDATION = "RED_P29_TOOL_MEDIATED_WORKBENCH_CONSOLIDATION_FAILED"

SOAK_ITERATION_COUNT = 5

TOOL_REQUEST_TYPES = frozenset({
    "local_read",
    "local_write",
    "web_fetch",
    "external_provider_call",
    "patch_application",
    "deletion",
    "authority_grant",
})

SANDBOX_RESULT_STATES = frozenset({
    "DRY_RUN_COMPLETE",
    "REFUSED_BY_POLICY",
    "REFUSED_MISSING_APPROVAL",
})

REFUSAL_REASONS = frozenset({
    "live_web_request",
    "external_provider_request",
    "filesystem_write_request",
    "patch_application_request",
    "deletion_request",
    "authority_grant_request",
    "domain_pack_claims_tool_permission",
    "operator_approval_missing",
})

RECORD_TYPES = {
    "tool_workbench_policy_v1",
    "tool_request_v1",
    "tool_plan_v1",
    "tool_sandbox_result_v1",
    "tool_receipt_v1",
    "tool_refusal_record_v1",
    "tool_workbench_gate_result_v1",
}

P29_INVARIANTS = {
    "P29-INV-01": "tool_plan_is_not_permission",
    "P29-INV-02": "tool_request_is_not_execution",
    "P29-INV-03": "sandbox_result_is_not_live_result",
    "P29-INV-04": "dry_run_is_not_live_effect",
    "P29-INV-05": "tool_receipt_is_not_authority",
    "P29-INV-06": "domain_pack_does_not_grant_tools",
    "P29-INV-07": "no_tool_authorization",
    "P29-INV-08": "no_live_effects",
    "P29-INV-09": "no_web_provider",
    "P29-INV-10": "no_patch_application",
    "P29-INV-11": "no_deletion",
    "P29-INV-12": "phase19_yellow_preserved",
    "P29-INV-13": "phase24_infrastructure_only_preserved",
}


def neutral_flags() -> dict[str, bool]:
    return {
        "tool_plan_treated_as_permission": False,
        "tool_request_executed_live": False,
        "sandbox_result_treated_as_live": False,
        "dry_run_treated_as_live_effect": False,
        "tool_receipt_treated_as_authority": False,
        "domain_pack_treated_as_tool_permission": False,
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


class ToolWorkbenchBoundaryError(ValueError):
    """P29 boundary violation."""


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise ToolWorkbenchBoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
