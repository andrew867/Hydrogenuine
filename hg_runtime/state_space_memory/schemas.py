"""F02 state-space memory organ schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "F02"
LEGACY_PHASE_ID = "F02"

VERDICT_GREEN = "GREEN_F02_STATE_SPACE_MEMORY_ORGAN"
VERDICT_YELLOW = "YELLOW_F02_STATE_SPACE_MEMORY_PARTIAL"
VERDICT_RED = "RED_F02_STATE_SPACE_MEMORY_FAILED"
GATE_RESULT_SCHEMA = "f02_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

STATE_ESTIMATE_IS_NOT_TRUTH = "State estimate is not truth."
MEMORY_IS_NOT_EVIDENCE = "Memory is not evidence by itself."
COMPRESSED_MEMORY_IS_LOSSY = "Compressed memory is lossy."
RECALL_IS_NOT_AUTHORITY = "Recall is not authority."
STATE_PREDICTION_IS_NOT_PERMISSION = "State prediction is not permission."
REPAIR_RECOMMENDATION_IS_NOT_PERMISSION = "Repair recommendation is not permission."
REPAIR_RECOMMENDATION_IS_NOT_PATCH_APPROVAL = "Repair recommendation is not patch approval."
RECOMMENDATION_DOES_NOT_AUTHORIZE_TOOLS = "Recommendation does not authorize tools."


class StateSpaceMemoryError(Exception):
    pass


def reject_memory_overreach(payload: dict) -> None:
    for key in (
        "state_estimate_is_truth",
        "memory_is_evidence",
        "recall_is_authority",
        "state_prediction_is_permission",
        "recommendation_is_permission",
        "recommendation_is_patch_approval",
        "recommendation_authorizes_tools",
        "query_authorizes_actions",
        "memory_mutates_authority",
        "memory_marks_phase19_green",
        "memory_marks_phase24_full_overnight_green",
        "memory_enables_live_provider",
        "memory_creates_live_effect",
        "memory_touches_hg_local",
        "memory_applies_patch",
        "claims_agi",
    ):
        if payload.get(key):
            raise StateSpaceMemoryError(
                f"State-space memory boundary violation: {key} must not be truthy"
            )
