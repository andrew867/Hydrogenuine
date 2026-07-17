"""WMBR-06 / CAGI-47 world-model audit schemas and boundaries."""

from __future__ import annotations

from typing import Any, Mapping

AUDIT_MANIFEST_SCHEMA = "world_model_audit_manifest_v1"
RECORD_AUDIT_SCHEMA = "world_model_record_audit_v1"
STALE_MARKER_SCHEMA = "stale_record_marker_v1"
DECAY_RECORD_SCHEMA = "decay_record_v1"
CONTRADICTION_AUDIT_SCHEMA = "contradiction_audit_record_v1"
FAILED_PREDICTION_AUDIT_SCHEMA = "failed_prediction_audit_record_v1"
RETRACTION_CLOSURE_SCHEMA = "retraction_closure_record_v1"
MAINTENANCE_POLICY_SCHEMA = "maintenance_policy_receipt_v1"
REPLAY_RECORD_SCHEMA = "audit_replay_record_v1"
GATE_RESULT_SCHEMA = "wmbr_06_gate_result_v1"

PHASE_ID = "WMBR-06"
LEGACY_PHASE_ID = "CAGI-47"
PARENT_PHASE_ID = "WMBR-01"
LEGACY_PARENT_PHASE_ID = "CAGI-42"
SOURCE_PHASE_ID = "WMBR-05"
SOURCE_LEGACY_PHASE_ID = "CAGI-46"

VERDICT_GREEN = "GREEN_WMBR_06_WORLD_MODEL_AUDIT_DECAY_RETRACTION"
VERDICT_YELLOW = "YELLOW_WMBR_06_WORLD_MODEL_AUDIT_PARTIAL"
VERDICT_RED = "RED_WMBR_06_WORLD_MODEL_AUDIT_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
WMBR_05_VERDICT_GREEN = "GREEN_WMBR_05_PREDICTIVE_CALIBRATION_UNCERTAINTY"
WMBR_04_VERDICT_GREEN = "GREEN_WMBR_04_CAUSAL_WORLD_MODEL_BOUNDARY"
WMBR_03_VERDICT_GREEN = "GREEN_WMBR_03_BELIEF_REVISION_LEDGER"
RUNTIME_P42_VERDICT_GREEN = "GREEN_PHASE42_PROVIDER_PORTABILITY_CROSS_MODEL_RECEIPT_SUBSTRATE"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
DOCTRINE = "Every model is a compressed civilization artifact."

DECAY_ACTIONS = ("MARK_STALE", "MARK_FOR_REVIEW", "APPEND_DECAY_NOTE")
STALE_REASONS = (
    "INSUFFICIENT_CONTEXT",
    "CONTRADICTED_HYPOTHESIS",
    "RETRACTED_SOURCE",
    "LOW_CONFIDENCE",
    "UNRESOLVED_DRIFT",
    "SYNTHETIC_MISMATCH_VISIBLE",
)
AUDIT_STATUSES = ("OPEN", "ACKNOWLEDGED", "CLOSED_WITH_RECEIPT", "REQUIRES_OPERATOR_REVIEW")

# Doctrine / boundary statements.
BELIEF_STATE_IS_NOT_TRUTH = "A belief state is not truth."
CAUSAL_HYPOTHESIS_IS_NOT_TRUTH = "A causal hypothesis is not causal truth."
PREDICTION_IS_NOT_VERIFICATION = "A prediction is not verification."
CALIBRATION_IS_NOT_PROOF = "A calibration record is not proof."
DECAY_IS_NOT_DELETION = "Decay is not deletion."
RETRACTION_IS_NOT_ERASURE = "Retraction is not erasure."
AUDIT_CLOSURE_IS_NOT_LAUNDERING = "Audit closure is not laundering."
FAILED_PREDICTION_REMAINS_VISIBLE = "A failed prediction must remain visible."
CONTRADICTION_REMAINS_VISIBLE = "A contradiction must remain visible."
STALE_RECORD_REMAINS_VISIBLE = "A stale record must remain visible."


class WorldModelAuditError(ValueError):
    """WMBR-06 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "truth_claimed": False,
        "certainty_claimed": False,
        "belief_state_treated_as_truth": False,
        "causal_hypothesis_treated_as_truth": False,
        "prediction_treated_as_verification": False,
        "calibration_treated_as_proof": False,
        "audit_closure_treated_as_laundering": False,
        "decay_treated_as_deletion": False,
        "retraction_treated_as_erasure": False,
        "deletion_performed": False,
        "rewrite_performed": False,
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
    "belief_state_treated_as_truth": "belief_state_treated_as_truth",
    "causal_hypothesis_treated_as_truth": "causal_hypothesis_treated_as_truth",
    "prediction_treated_as_verification": "prediction_treated_as_verification",
    "prediction_verified": "prediction_marked_verified",
    "calibration_treated_as_proof": "calibration_treated_as_proof",
    "calibration_is_proof": "calibration_treated_as_proof",
    "audit_closure_treated_as_laundering": "audit_closure_treated_as_laundering",
    "decay_treated_as_deletion": "decay_treated_as_deletion",
    "retraction_treated_as_erasure": "retraction_treated_as_erasure",
    "deletion_performed": "deletion_performed",
    "rewrite_performed": "rewrite_performed",
    "live_observation": "live_observation",
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
            raise WorldModelAuditError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
