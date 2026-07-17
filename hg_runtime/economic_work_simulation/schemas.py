"""SIEW-01 / CAGI-63 economic work simulation schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "SIEW-01"
LEGACY_PHASE_ID = "CAGI-63"
PARENT_PHASE_ID = "BSI-03"

VERDICT_GREEN = "GREEN_P63_ECONOMIC_WORK_SIMULATION"
VERDICT_YELLOW = "YELLOW_P63_ECONOMIC_WORK_SIMULATION_PARTIAL"
VERDICT_RED = "RED_P63_ECONOMIC_WORK_SIMULATION_FAILED"
GATE_RESULT_SCHEMA = "siew_01_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

SIMULATION_ONLY = "SIMULATION_ONLY"
ECONOMIC_SCORE_IS_NOT_REAL_VALUE = "Economic score is not real value."
SIMULATED_WORK_IS_NOT_CUSTOMER_WORK = "Simulated work is not customer work."
NO_EXTERNAL_CUSTOMER = "No external customer."
NO_PAYMENT = "No payment or money movement."

TASK_STATUS_DRAFT = "TASK_DRAFT"
TASK_STATUS_SIMULATED = "TASK_SIMULATED"
TASK_STATUS_COMPLETED_SIMULATED = "TASK_COMPLETED_SIMULATED"

TASK_DOMAINS = frozenset({
    "DOCUMENTATION",
    "TEST_WRITING",
    "CODE_REVIEW",
    "BUG_TRIAGE",
    "RESEARCH_SUMMARY",
    "DATA_ANALYSIS",
    "CONFIGURATION",
    "REPORT_GENERATION",
})


class EconomicWorkSimulationError(Exception):
    pass


def reject_real_economic_work(payload: dict) -> None:
    for key in (
        "real_customer",
        "real_payment",
        "money_movement",
        "invoice_created",
        "tool_authorized",
        "tool_executed",
        "external_contact",
        "web_call",
        "provider_call",
        "live_submission",
        "deployment_claim",
        "claims_agi",
    ):
        if payload.get(key):
            raise EconomicWorkSimulationError(
                f"Economic work boundary violation: {key} must not be truthy"
            )
