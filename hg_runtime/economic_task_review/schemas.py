"""SIEW-02 / CAGI-64 economic task review schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "SIEW-02"
LEGACY_PHASE_ID = "CAGI-64"
PARENT_PHASE_ID = "SIEW-01"

VERDICT_GREEN = "GREEN_P64_ECONOMIC_TASK_REVIEW_RECEIPTS"
VERDICT_YELLOW = "YELLOW_P64_ECONOMIC_TASK_REVIEW_PARTIAL"
VERDICT_RED = "RED_P64_ECONOMIC_TASK_REVIEW_FAILED"
GATE_RESULT_SCHEMA = "siew_02_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

REVIEW_STATUS_PENDING = "REVIEW_PENDING"
REVIEW_STATUS_COMPLETED = "REVIEW_COMPLETED"
QUALITY_PASS = "QUALITY_PASS"
QUALITY_FAIL = "QUALITY_FAIL"
QUALITY_UNCERTAIN = "QUALITY_UNCERTAIN"

REVIEW_IS_NOT_CUSTOMER_ACCEPTANCE = "A review pass is not customer acceptance."
REVIEW_IS_NOT_PAYMENT_PERMISSION = "A review pass is not payment permission."
NO_LIVE_SUBMISSION = "No live submission."


class EconomicTaskReviewError(Exception):
    pass


def reject_real_acceptance(payload: dict) -> None:
    for key in (
        "customer_accepted",
        "payment_permitted",
        "invoice_sent",
        "live_submitted",
        "tool_authorized",
        "external_action",
        "money_movement",
        "deployment_claim",
        "claims_agi",
    ):
        if payload.get(key):
            raise EconomicTaskReviewError(
                f"Review boundary violation: {key} must not be truthy"
            )
