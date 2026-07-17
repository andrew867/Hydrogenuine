"""P69 field trial readiness boundary schemas."""

from __future__ import annotations

PHASE_ID = "P69"
VERDICT_GREEN = "GREEN_P69_FIELD_TRIAL_READINESS_BOUNDARY"
VERDICT_YELLOW = "YELLOW_P69_FIELD_TRIAL_READINESS_PARTIAL"
VERDICT_RED = "RED_P69_FIELD_TRIAL_READINESS_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

FIELD_READINESS_IS_NOT_FIELD_TRIAL = "Field readiness is not a field trial."
REHEARSAL_IS_NOT_LIVE_TRIAL = "Rehearsal is not a live trial."
READINESS_GREEN_IS_NOT_DEPLOYMENT = "Readiness GREEN is not deployment permission."


class FieldTrialReadinessError(Exception):
    pass


def reject_readiness_overreach(payload: dict) -> None:
    for key in (
        "live_field_trial_authorized",
        "deployment_permission_claimed",
        "live_trial_started",
        "live_effect_created",
        "tool_authorized",
        "external_provider_enabled",
        "social_post_published",
        "customer_contacted",
        "message_sent",
        "money_movement",
        "patch_applied",
        "authority_mutated",
        "hg_local_touched",
        "phase19_green_claimed",
        "phase24_full_overnight_green_claimed",
        "claims_agi",
        "claims_consciousness",
        "claims_sovereignty",
        "self_authorization",
        "web_browse_performed",
    ):
        if payload.get(key):
            raise FieldTrialReadinessError(
                f"Readiness boundary violation: {key} must not be truthy"
            )
