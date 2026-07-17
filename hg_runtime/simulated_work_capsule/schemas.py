"""F12A simulated work capsule schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "F12A"
PARENT_PHASE_IDS = ("SIEW-01", "SIEW-02", "SIEW-03", "F02")

VERDICT_GREEN = "GREEN_F12A_SIMULATED_SOCIAL_ECONOMIC_WORK_CAPSULE"
VERDICT_YELLOW = "YELLOW_F12A_SIMULATED_WORK_CAPSULE_PARTIAL"
VERDICT_RED = "RED_F12A_SIMULATED_WORK_CAPSULE_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

CAPSULE_IS_SIMULATED_ONLY = "Capsule is simulated only."
SIMULATED_WORK_IS_NOT_CUSTOMER_WORK = "Simulated work is not customer work."
SOCIAL_OUTPUT_IS_NOT_SOCIAL_POST = "Social output is not a social post."
REVIEW_PASS_IS_NOT_CUSTOMER_ACCEPTANCE = "Review pass is not customer acceptance."
VALUE_ESTIMATE_IS_NOT_PAYMENT_PERMISSION = "Value estimate is not payment permission."
F02_MEMORY_REFERENCE_IS_NOT_TRUTH = "F02 memory reference is not truth."
F02_REPAIR_RECOMMENDATION_IS_NOT_PERMISSION = "F02 repair recommendation is not permission."

CAPSULE_TASK_DOMAINS = frozenset({
    "KNOWLEDGE_WORK",
    "SOCIAL_DRAFT",
    "ECONOMIC_EVALUATION",
    "MAINTENANCE",
    "REVIEW",
    "DEFECT_TRIAGE",
    "REPORT_GENERATION",
})


class SimulatedWorkCapsuleError(Exception):
    pass


def reject_capsule_overreach(payload: dict) -> None:
    for key in (
        "real_customer",
        "customer_contact",
        "social_post_published",
        "message_sent",
        "real_payment",
        "money_movement",
        "invoice_created",
        "tool_authorized",
        "tool_executed",
        "patch_applied",
        "authority_mutated",
        "live_effect",
        "live_provider_enabled",
        "live_submission",
        "hg_local_touched",
        "deployment_claim",
        "claims_agi",
        "phase19_green_claimed",
        "phase24_full_overnight_green_claimed",
        "self_modification",
        "web_browse_performed",
        "external_provider_call",
    ):
        if payload.get(key):
            raise SimulatedWorkCapsuleError(
                f"Capsule boundary violation: {key} must not be truthy"
            )
