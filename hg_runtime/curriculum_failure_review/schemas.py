"""AEC-05 / CAGI-52 curriculum failure review schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "AEC-05"
LEGACY_PHASE_ID = "CAGI-52"
PARENT_PHASE_ID = "AEC-04"

VERDICT_GREEN = "GREEN_AEC_05_CURRICULUM_FAILURE_REVIEW"
VERDICT_YELLOW = "YELLOW_AEC_05_CURRICULUM_FAILURE_PARTIAL"
VERDICT_RED = "RED_AEC_05_CURRICULUM_FAILURE_FAILED"
GATE_RESULT_SCHEMA = "aec_05_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

FAILURE_STATUS_QUEUED = "QUEUED_FOR_REVIEW"
FAILURE_STATUS_REVIEWED = "REVIEWED_NOT_ACTED"
ROOT_CAUSE_STATUS_HYPOTHESIS = "ROOT_CAUSE_HYPOTHESIS"

FAILURE_CATEGORIES = ("ACCURACY_DROP", "CALIBRATION_MISS", "SAFETY_VIOLATION", "TRANSFER_DEGRADATION", "REFUSAL_ERROR")
ROOT_CAUSE_TYPES = ("DATA_GAP", "PROMPT_SENSITIVITY", "DOMAIN_MISMATCH", "BOUNDARY_MISCONFIGURATION", "UNKNOWN")

FAILURE_IS_NOT_DEFECT = "A curriculum failure is not a product defect."
REVIEW_IS_NOT_FIX = "A failure review is not a fix or patch."
ROOT_CAUSE_IS_NOT_DIAGNOSIS = "A root cause hypothesis is not a confirmed diagnosis."


class CurriculumFailureReviewError(Exception):
    pass


def reject_live_failure_action(payload: dict) -> None:
    for key in (
        "apply_fix",
        "deploy_patch",
        "live_execution_enabled",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
    ):
        if payload.get(key):
            raise CurriculumFailureReviewError(
                f"Live failure action boundary violation: {key} must not be truthy"
            )
