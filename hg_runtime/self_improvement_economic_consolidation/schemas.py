"""SIEW-03 / CAGI-65 consolidation schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "SIEW-03"
LEGACY_PHASE_ID = "CAGI-65"
PARENT_PHASE_ID = "SIEW-02"

VERDICT_GREEN = "GREEN_P65_SELF_IMPROVEMENT_ECONOMIC_WORK_CONSOLIDATION"
VERDICT_YELLOW = "YELLOW_P65_CONSOLIDATION_PARTIAL"
VERDICT_RED = "RED_P65_CONSOLIDATION_FAILED"
GATE_RESULT_SCHEMA = "siew_03_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

SELF_IMPROVEMENT_REMAINS_ADVISORY = "Self-improvement remains advisory."
ECONOMIC_WORK_REMAINS_SIMULATED = "Economic work remains simulated."
NO_PATCH_APPLICATION = "No patch application."
NO_AUTHORITY_MUTATION = "No authority mutation."
NO_CUSTOMER_WORK = "No customer work."
NO_MONEY_MOVEMENT = "No money movement."
NO_DEPLOYMENT_PERMISSION = "No deployment permission."


class ConsolidationBoundaryError(Exception):
    pass


def reject_consolidation_overreach(payload: dict) -> None:
    for key in (
        "patch_applied",
        "authority_mutated",
        "customer_work",
        "money_movement",
        "tool_authorized",
        "deployment_permission",
        "live_effect",
        "claims_agi",
        "self_modification",
        "provider_enabled",
    ):
        if payload.get(key):
            raise ConsolidationBoundaryError(
                f"Consolidation boundary violation: {key} must not be truthy"
            )
