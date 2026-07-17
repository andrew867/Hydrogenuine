"""WMBR-05 / CAGI-46 predictive calibration schemas and boundaries."""

from __future__ import annotations

from typing import Any, Mapping

PREDICTION_CANDIDATE_SCHEMA = "prediction_candidate_v1"
SYNTHETIC_OUTCOME_SCHEMA = "synthetic_outcome_receipt_v1"
CALIBRATION_RECORD_SCHEMA = "calibration_record_v1"
UNCERTAINTY_SCORE_SCHEMA = "uncertainty_score_record_v1"
PREDICTION_DRIFT_SCHEMA = "prediction_drift_record_v1"
CALIBRATION_MANIFEST_SCHEMA = "calibration_manifest_v1"
REPLAY_RECORD_SCHEMA = "predictive_calibration_replay_record_v1"
GATE_RESULT_SCHEMA = "wmbr_05_gate_result_v1"

PHASE_ID = "WMBR-05"
LEGACY_PHASE_ID = "CAGI-46"
PARENT_PHASE_ID = "WMBR-01"
LEGACY_PARENT_PHASE_ID = "CAGI-42"
SOURCE_PHASE_ID = "WMBR-04"
SOURCE_LEGACY_PHASE_ID = "CAGI-45"

VERDICT_GREEN = "GREEN_WMBR_05_PREDICTIVE_CALIBRATION_UNCERTAINTY"
VERDICT_YELLOW = "YELLOW_WMBR_05_PREDICTIVE_CALIBRATION_PARTIAL"
VERDICT_RED = "RED_WMBR_05_PREDICTIVE_CALIBRATION_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
WMBR_04_VERDICT_GREEN = "GREEN_WMBR_04_CAUSAL_WORLD_MODEL_BOUNDARY"
WMBR_03_VERDICT_GREEN = "GREEN_WMBR_03_BELIEF_REVISION_LEDGER"
WMBR_02_VERDICT_GREEN = "GREEN_WMBR_02_BELIEF_CONFLICT_VERIFICATION_QUEUE"
WMBR_01A_VERDICT_GREEN = "GREEN_WMBR_01A_CROSS_MODEL_PERSPECTIVE_MATRIX"
RUNTIME_P42_VERDICT_GREEN = "GREEN_PHASE42_PROVIDER_PORTABILITY_CROSS_MODEL_RECEIPT_SUBSTRATE"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
DOCTRINE = "Every model is a compressed civilization artifact."

PREDICTION_KINDS = ("DIRECTIONAL", "NUMERIC", "TEMPORAL", "CLASSIFICATION", "QUALITATIVE")
PREDICTION_STATUSES = ("PROPOSED_UNTESTED", "SYNTHETIC_OUTCOME_ATTACHED", "INSUFFICIENT_CONTEXT")
OUTCOME_KINDS = ("SYNTHETIC_MATCH", "SYNTHETIC_MISMATCH", "SYNTHETIC_PARTIAL", "SYNTHETIC_UNKNOWN")
SCORE_KINDS = ("EXACT_MATCH", "PARTIAL_MATCH", "MISMATCH", "UNKNOWN")
UNCERTAINTY_LEVELS = ("LOW", "MEDIUM", "HIGH", "UNKNOWN")
DRIFT_TYPES = ("SYNTHETIC_MISMATCH", "INSUFFICIENT_CONTEXT", "CONTRADICTED_HYPOTHESIS", "RETRACTED_SOURCE")

EMIT_PREDICTION_STATUSES = ("PROPOSED",)
INSUFFICIENT_CONTEXT_STATUSES = ("CONTRADICTED", "INSUFFICIENT_EVIDENCE", "RETRACTED", "NEEDS_TEST")

# Doctrine / boundary statements.
CAUSAL_HYPOTHESIS_IS_NOT_TRUTH = "A causal hypothesis is not causal truth."
PREDICTION_IS_NOT_VERIFICATION = "A prediction is not verification."
CALIBRATION_IS_NOT_PROOF = "A calibration record is not proof."
UNCERTAINTY_IS_NOT_PERMISSION = "An uncertainty score is not permission."
CONFIDENCE_IS_NOT_AUTHORITY = "A confidence score is not authority."
SYNTHETIC_OUTCOME_IS_NOT_LIVE_OBSERVATION = "A synthetic outcome is not a live observation."
FAILED_PREDICTION_REMAINS_VISIBLE = "A failed prediction must remain visible."
SUCCESSFUL_PREDICTION_REMAINS_PROVISIONAL = "A successful prediction must remain provisional."


class PredictiveCalibrationError(ValueError):
    """WMBR-05 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "truth_claimed": False,
        "certainty_claimed": False,
        "causal_hypothesis_treated_as_truth": False,
        "prediction_is_verification": False,
        "prediction_treated_as_verification": False,
        "prediction_verified": False,
        "calibration_is_proof": False,
        "calibration_treated_as_proof": False,
        "uncertainty_is_permission": False,
        "confidence_is_authority": False,
        "synthetic_outcome_treated_as_live_observation": False,
        "live_observation": False,
        "external_call_made": False,
        "external_provider_call_made": False,
        "external_provider_calls_made": False,
        "web_browse_performed": False,
        "action_authorized": False,
        "authority_granted": False,
        "tools_authorized": False,
        "tool_authorized": False,
        "live_effects_created": False,
        "live_external_side_effects_created": False,
        "new_live_posts_created": False,
        "claims_agi": False,
        "candidate_agi_parent_phase_completed": False,
    }


FORBIDDEN_TRUE = {
    "truth_claimed": "truth_claimed",
    "certainty_claimed": "certainty_claimed",
    "causal_hypothesis_treated_as_truth": "causal_hypothesis_treated_as_truth",
    "prediction_is_verification": "prediction_treated_as_verification",
    "prediction_treated_as_verification": "prediction_treated_as_verification",
    "prediction_verified": "prediction_marked_verified",
    "calibration_is_proof": "calibration_treated_as_proof",
    "calibration_treated_as_proof": "calibration_treated_as_proof",
    "uncertainty_is_permission": "uncertainty_treated_as_permission",
    "confidence_is_authority": "confidence_treated_as_authority",
    "synthetic_outcome_treated_as_live_observation": "synthetic_outcome_treated_as_live",
    "live_observation": "synthetic_outcome_treated_as_live",
    "external_call_made": "external_provider_call",
    "external_provider_call_made": "external_provider_call",
    "external_provider_calls_made": "external_provider_call",
    "web_browse_performed": "web_browse",
    "action_authorized": "action_authorized",
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "tool_authorized": "tools_authorized",
    "live_effects_created": "live_effect_created",
    "live_external_side_effects_created": "live_effect_created",
    "new_live_posts_created": "live_post_created",
    "claims_agi": "claims_agi_forbidden",
    "candidate_agi_parent_phase_completed": "candidate_agi_parent_phase_completion_claim",
}


def assert_neutral(payload: Mapping[str, Any]) -> None:
    """Recursively refuse any artifact that asserts a forbidden truth/authority flag."""
    for key, value in payload.items():
        if value and str(key) in FORBIDDEN_TRUE:
            raise PredictiveCalibrationError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
