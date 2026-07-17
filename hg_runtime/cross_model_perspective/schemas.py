"""WMBR-01A / CAGI-42A cross-model perspective schemas and boundaries."""

from __future__ import annotations

from typing import Any, Mapping

PERSPECTIVE_MATRIX_SCHEMA = "perspective_matrix_v1"
PERSPECTIVE_MATRIX_CELL_SCHEMA = "perspective_matrix_cell_v1"
DIVERGENCE_MATRIX_SCHEMA = "divergence_matrix_v1"
DIVERGENCE_RECORD_SCHEMA = "divergence_record_v1"
OMISSION_PATTERN_SCHEMA = "omission_pattern_v1"
REFUSAL_PATTERN_SCHEMA = "refusal_pattern_v1"
FRAMING_SIGNATURE_SCHEMA = "framing_signature_v1"
MORAL_CONSENSUS_MATRIX_SCHEMA = "moral_consensus_matrix_v1"
MORAL_CONFLICT_RECORD_SCHEMA = "moral_conflict_record_v1"
EVIDENCE_GAP_TASK_SCHEMA = "evidence_gap_task_v1"
SUMMARY_SCHEMA = "cross_model_perspective_summary_v1"
REPLAY_RECORD_SCHEMA = "cross_model_perspective_replay_record_v1"
GATE_RESULT_SCHEMA = "wmbr_01a_gate_result_v1"

PHASE_ID = "WMBR-01A"
LEGACY_PHASE_ID = "CAGI-42A"
PARENT_PHASE_ID = "WMBR-01"
LEGACY_PARENT_PHASE_ID = "CAGI-42"

VERDICT_GREEN = "GREEN_WMBR_01A_CROSS_MODEL_PERSPECTIVE_MATRIX"
VERDICT_YELLOW = "YELLOW_WMBR_01A_PERSPECTIVE_MATRIX_PARTIAL"
VERDICT_RED = "RED_WMBR_01A_PERSPECTIVE_MATRIX_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
RUNTIME_P42_VERDICT_GREEN = "GREEN_PHASE42_PROVIDER_PORTABILITY_CROSS_MODEL_RECEIPT_SUBSTRATE"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
DOCTRINE = "Every model is a compressed civilization artifact."

# Descriptive, non-truth / non-authority boundary statements reused across artifacts.
CONSENSUS_IS_NOT_TRUTH = "Model consensus is recorded descriptively and is not treated as truth or proof."
DISAGREEMENT_IS_NOT_EVIDENCE = "Model disagreement is recorded descriptively and is not treated as evidence by itself."
REFUSAL_IS_NOT_AUTHORITY = "Model refusal is recorded descriptively and is not treated as authority."
WILLINGNESS_IS_NOT_PERMISSION = "Model willingness is recorded descriptively and is not treated as permission."
MORAL_CONSENSUS_IS_NOT_AUTHORITY = "Shared moral framing is recorded descriptively and is not treated as moral authority."
OMISSION_IS_NOT_PROOF = "Omission is recorded descriptively and is not treated as proof of intent."
FRAMING_IS_DESCRIPTIVE = "Framing signatures are descriptive only and are not treated as truth or authority."
EVIDENCE_GAP_TASK_IS_NOT_ACTION = "Evidence gap tasks are verification follow-ups only; they are not actions and authorize no tools."


class CrossModelPerspectiveError(ValueError):
    """WMBR-01A validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
        "live_external_side_effects_created": False,
        "external_provider_call_made": False,
        "external_provider_calls_made": False,
        "model_output_treated_as_truth": False,
        "model_consensus_treated_as_truth": False,
        "model_disagreement_treated_as_evidence": False,
        "model_refusal_treated_as_authority": False,
        "model_willingness_treated_as_permission": False,
        "moral_consensus_treated_as_authority": False,
        "moral_claim_treated_as_authority": False,
        "evidence_gap_tasks_authorize_actions": False,
        "new_live_posts_created": False,
        "claims_agi": False,
        "candidate_agi_phase_completed": False,
        "candidate_agi_parent_phase_completed": False,
    }


FORBIDDEN_TRUE = {
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "live_effects_created": "live_effect_created",
    "live_external_side_effects_created": "live_effect_created",
    "external_provider_call_made": "external_provider_call",
    "external_provider_calls_made": "external_provider_call",
    "model_output_treated_as_truth": "model_output_treated_as_truth",
    "model_consensus_treated_as_truth": "model_consensus_treated_as_truth",
    "model_disagreement_treated_as_evidence": "model_disagreement_treated_as_evidence",
    "model_refusal_treated_as_authority": "model_refusal_treated_as_authority",
    "model_willingness_treated_as_permission": "model_willingness_treated_as_permission",
    "moral_consensus_treated_as_authority": "moral_consensus_treated_as_authority",
    "moral_claim_treated_as_authority": "moral_claim_treated_as_authority",
    "evidence_gap_tasks_authorize_actions": "evidence_gap_tasks_authorize_actions",
    "new_live_posts_created": "live_post_created",
    "claims_agi": "claims_agi_forbidden",
    "candidate_agi_phase_completed": "candidate_agi_phase_completion_claim",
    "candidate_agi_parent_phase_completed": "candidate_agi_parent_phase_completion_claim",
}


def assert_neutral(payload: Mapping[str, Any]) -> None:
    """Recursively refuse any artifact that asserts a forbidden authority/truth flag."""
    for key, value in payload.items():
        if value and str(key) in FORBIDDEN_TRUE:
            raise CrossModelPerspectiveError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
