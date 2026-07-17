"""P70 evidence field review schemas."""

from __future__ import annotations

PHASE_ID = "P70"
VERDICT_GREEN = "GREEN_P70_EXTERNAL_FIELD_REPRODUCTION_EVIDENCE_REVIEW"
VERDICT_YELLOW = "YELLOW_P70_EVIDENCE_FIELD_REVIEW_PARTIAL"
VERDICT_RED = "RED_P70_EVIDENCE_FIELD_REVIEW_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

REPRODUCTION_IS_NOT_LIVE_TRIAL = "Reproduction packet is not a live trial."
FIELD_REVIEW_IS_NOT_TRUTH = "Field review is not truth."
REVIEWER_NOTE_IS_NOT_AUTHORITY = "Reviewer note is not authority."
REPRODUCTION_PASS_IS_NOT_DEPLOYMENT = "Reproduction pass is not deployment permission."


class EvidenceFieldReviewError(Exception):
    pass


def reject_evidence_overreach(payload: dict) -> None:
    for key in (
        "reproduction_treated_as_truth",
        "reviewer_note_treated_as_authority",
        "reproduction_is_deployment_permission",
        "live_trial_authorized",
        "live_effect_created",
        "tool_authorized",
        "external_provider_enabled",
        "discrepancy_suppressed",
        "unresolved_gap_suppressed",
        "patch_applied",
        "authority_mutated",
        "hg_local_touched",
        "phase19_green_claimed",
        "phase24_full_overnight_green_claimed",
        "claims_agi",
        "claims_consciousness",
        "claims_sovereignty",
        "deployment_permission_claimed",
        "web_browse_performed",
    ):
        if payload.get(key):
            raise EvidenceFieldReviewError(
                f"Evidence review boundary violation: {key} must not be truthy"
            )
