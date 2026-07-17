"""CLIFT-03 / CAGI-68 local inference operations schemas."""

from __future__ import annotations

PHASE_ID = "CLIFT-03"
LEGACY_PHASE_ID = "CAGI-68"
PARENT_PHASE_ID = "CLIFT-02"

VERDICT_GREEN = "GREEN_P68_LOCAL_INFERENCE_OPERATIONS"
VERDICT_YELLOW = "YELLOW_P68_LOCAL_INFERENCE_PARTIAL"
VERDICT_RED = "RED_P68_LOCAL_INFERENCE_FAILED"
GATE_RESULT_SCHEMA = "clift_03_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

LOCAL_OUTPUT_IS_NOT_TRUTH = "Local model output is not truth."
LOCAL_INFERENCE_IS_NOT_AUTHORITY = "Local inference is not authority."
LOCAL_AVAILABILITY_IS_NOT_PERMISSION = "Local availability is not permission."
LARGE_MODEL_REQUIRES_EXPLICIT_CONFIG = "30B-class load requires explicit operator configuration."
PROVIDER_DISABLED_BY_DEFAULT = "Provider disabled by default."

LARGE_MODEL_THRESHOLD_B = 30


class LocalInferenceError(Exception):
    pass


def reject_inference_overreach(payload: dict) -> None:
    for key in (
        "inference_treated_as_authority",
        "output_treated_as_truth",
        "availability_treated_as_permission",
        "provider_enabled_by_default",
        "large_model_default_load",
        "network_required",
        "external_provider_call",
        "tool_authorized",
        "hg_local_accessed",
        "live_effect_created",
        "claims_agi",
    ):
        if payload.get(key):
            raise LocalInferenceError(
                f"Local inference boundary violation: {key} must not be truthy"
            )
