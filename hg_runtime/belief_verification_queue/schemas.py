"""WMBR-02 / CAGI-43 belief-verification-queue schemas and boundaries."""

from __future__ import annotations

from typing import Any, Mapping

BELIEF_CONFLICT_RECORD_SCHEMA = "belief_conflict_record_v1"
CANDIDATE_CLAIM_RECORD_SCHEMA = "candidate_claim_record_v1"
VERIFICATION_TASK_SCHEMA = "verification_task_v1"
VERIFICATION_QUEUE_MANIFEST_SCHEMA = "verification_queue_manifest_v1"
EVIDENCE_POLICY_RECEIPT_SCHEMA = "evidence_policy_receipt_v1"
VERIFICATION_PRIORITY_RECORD_SCHEMA = "verification_priority_record_v1"
REPLAY_RECORD_SCHEMA = "verification_replay_record_v1"
GATE_RESULT_SCHEMA = "wmbr_02_gate_result_v1"

PHASE_ID = "WMBR-02"
LEGACY_PHASE_ID = "CAGI-43"
PARENT_PHASE_ID = "WMBR-01"
LEGACY_PARENT_PHASE_ID = "CAGI-42"
SOURCE_PHASE_ID = "WMBR-01A"

VERDICT_GREEN = "GREEN_WMBR_02_BELIEF_CONFLICT_VERIFICATION_QUEUE"
VERDICT_YELLOW = "YELLOW_WMBR_02_VERIFICATION_QUEUE_PARTIAL"
VERDICT_RED = "RED_WMBR_02_VERIFICATION_QUEUE_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
WMBR_01A_VERDICT_GREEN = "GREEN_WMBR_01A_CROSS_MODEL_PERSPECTIVE_MATRIX"
RUNTIME_P42_VERDICT_GREEN = "GREEN_PHASE42_PROVIDER_PORTABILITY_CROSS_MODEL_RECEIPT_SUBSTRATE"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
DOCTRINE = "Every model is a compressed civilization artifact."

# Enumerations.
CONFLICT_TYPES = (
    "FACTUAL_DIVERGENCE",
    "FRAMING_DIVERGENCE",
    "REFUSAL_DIVERGENCE",
    "OMISSION_DIVERGENCE",
    "MORAL_CONFLICT",
    "UNSOURCED_CONSENSUS",
)
CLAIM_KINDS = ("FACTUAL", "HISTORICAL", "MORAL", "POLICY", "TECHNICAL", "UNCERTAIN")
CONFIDENCE_SOURCES = ("MODEL_ASSERTION", "MODEL_CONSENSUS", "MODEL_DIVERGENCE", "OPERATOR_FIXTURE")
TRUTH_STATUS_UNVERIFIED = "UNVERIFIED"
BELIEF_STATUS_NOT_PROMOTED = "NOT_PROMOTED"
TASK_STATUS_QUEUED = "QUEUED_NOT_AUTHORIZED"
TASK_TYPES = (
    "SOURCE_CHECK",
    "PRIMARY_SOURCE_REQUEST",
    "CROSS_REFERENCE_REQUEST",
    "DEFINITIONS_REQUEST",
    "TIMELINE_CHECK",
    "NUMERIC_CHECK",
    "POLICY_CONTEXT_CHECK",
)

# Doctrine / boundary statements reused in artifacts and the report.
SPECTROSCOPY_IS_NOT_BELIEF = "A spectroscopy artifact is not a belief."
CONFLICT_IS_NOT_EVIDENCE = "A belief-conflict record is not evidence."
TASK_IS_NOT_ACTION = "A verification task is not an action."
SOURCE_REQUEST_IS_NOT_TOOL_AUTH = "A source request is not a tool authorization."
CONSENSUS_IS_NOT_TRUTH = "Model consensus is not truth."
DIVERGENCE_IS_NOT_EVIDENCE = "Model divergence is not evidence by itself."
REFUSAL_IS_NOT_AUTHORITY = "Model refusal is not authority."
WILLINGNESS_IS_NOT_PERMISSION = "Model willingness is not permission."
MORAL_CONSENSUS_IS_NOT_AUTHORITY = "Moral consensus is not moral authority."


class BeliefVerificationQueueError(ValueError):
    """WMBR-02 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "authority_granted": False,
        "tools_authorized": False,
        "tool_authorized": False,
        "action_authorized": False,
        "external_call_authorized": False,
        "live_effects_created": False,
        "live_external_side_effects_created": False,
        "external_provider_call_made": False,
        "external_provider_calls_made": False,
        "web_browse_performed": False,
        "model_output_treated_as_evidence": False,
        "model_consensus_treated_as_evidence": False,
        "model_refusal_treated_as_evidence": False,
        "model_output_treated_as_truth": False,
        "model_consensus_treated_as_truth": False,
        "model_disagreement_treated_as_evidence": False,
        "moral_consensus_treated_as_authority": False,
        "conflict_record_treated_as_evidence": False,
        "verification_task_treated_as_action": False,
        "source_request_treated_as_external_call": False,
        "claim_marked_true": False,
        "claim_marked_false": False,
        "belief_promoted": False,
        "new_live_posts_created": False,
        "claims_agi": False,
        "candidate_agi_parent_phase_completed": False,
    }


FORBIDDEN_TRUE = {
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "tool_authorized": "tool_authorized",
    "action_authorized": "action_authorized",
    "external_call_authorized": "external_call_authorized",
    "live_effects_created": "live_effect_created",
    "live_external_side_effects_created": "live_effect_created",
    "external_provider_call_made": "external_provider_call",
    "external_provider_calls_made": "external_provider_call",
    "web_browse_performed": "web_browse",
    "model_output_treated_as_evidence": "model_output_treated_as_evidence",
    "model_consensus_treated_as_evidence": "model_consensus_treated_as_evidence",
    "model_refusal_treated_as_evidence": "model_refusal_treated_as_evidence",
    "model_output_treated_as_truth": "model_output_treated_as_truth",
    "model_consensus_treated_as_truth": "model_consensus_treated_as_truth",
    "model_disagreement_treated_as_evidence": "model_disagreement_treated_as_evidence",
    "moral_consensus_treated_as_authority": "moral_consensus_treated_as_authority",
    "conflict_record_treated_as_evidence": "conflict_record_treated_as_evidence",
    "verification_task_treated_as_action": "verification_task_treated_as_action",
    "source_request_treated_as_external_call": "source_request_treated_as_external_call",
    "claim_marked_true": "claim_marked_true",
    "claim_marked_false": "claim_marked_false",
    "belief_promoted": "belief_promoted",
    "new_live_posts_created": "live_post_created",
    "claims_agi": "claims_agi_forbidden",
    "candidate_agi_parent_phase_completed": "candidate_agi_parent_phase_completion_claim",
}


def assert_neutral(payload: Mapping[str, Any]) -> None:
    """Recursively refuse any artifact that asserts a forbidden authority/belief flag."""
    for key, value in payload.items():
        if value and str(key) in FORBIDDEN_TRUE:
            raise BeliefVerificationQueueError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
