"""WMBR-03 / CAGI-44 belief-revision-ledger schemas and boundaries."""

from __future__ import annotations

from typing import Any, Mapping

EVIDENCE_RECEIPT_SCHEMA = "evidence_receipt_v1"
BELIEF_STATE_RECORD_SCHEMA = "belief_state_record_v1"
BELIEF_REVISION_RECORD_SCHEMA = "belief_revision_record_v1"
CONTRADICTION_RECORD_SCHEMA = "contradiction_record_v1"
RETRACTION_RECORD_SCHEMA = "retraction_record_v1"
PROVENANCE_CHAIN_SCHEMA = "provenance_chain_v1"
MANIFEST_SCHEMA = "belief_revision_manifest_v1"
REPLAY_RECORD_SCHEMA = "belief_revision_replay_record_v1"
GATE_RESULT_SCHEMA = "wmbr_03_gate_result_v1"

PHASE_ID = "WMBR-03"
LEGACY_PHASE_ID = "CAGI-44"
PARENT_PHASE_ID = "WMBR-01"
LEGACY_PARENT_PHASE_ID = "CAGI-42"
SOURCE_PHASE_ID = "WMBR-02"
SOURCE_LEGACY_PHASE_ID = "CAGI-43"

VERDICT_GREEN = "GREEN_WMBR_03_BELIEF_REVISION_LEDGER"
VERDICT_YELLOW = "YELLOW_WMBR_03_BELIEF_REVISION_PARTIAL"
VERDICT_RED = "RED_WMBR_03_BELIEF_REVISION_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
WMBR_02_VERDICT_GREEN = "GREEN_WMBR_02_BELIEF_CONFLICT_VERIFICATION_QUEUE"
WMBR_01A_VERDICT_GREEN = "GREEN_WMBR_01A_CROSS_MODEL_PERSPECTIVE_MATRIX"
RUNTIME_P42_VERDICT_GREEN = "GREEN_PHASE42_PROVIDER_PORTABILITY_CROSS_MODEL_RECEIPT_SUBSTRATE"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
DOCTRINE = "Every model is a compressed civilization artifact."

# Belief lifecycle.
BELIEF_UNVERIFIED = "UNVERIFIED"
BELIEF_PROVISIONALLY_SUPPORTED = "PROVISIONALLY_SUPPORTED"
BELIEF_CONTRADICTED = "CONTRADICTED"
BELIEF_RETRACTED = "RETRACTED"
BELIEF_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
BELIEF_STATUSES = (
    BELIEF_UNVERIFIED,
    BELIEF_PROVISIONALLY_SUPPORTED,
    BELIEF_CONTRADICTED,
    BELIEF_RETRACTED,
    BELIEF_INSUFFICIENT,
)
# Statuses that count as "promoted" and therefore require a provenance chain.
PROMOTED_STATUSES = (BELIEF_PROVISIONALLY_SUPPORTED, BELIEF_CONTRADICTED, BELIEF_RETRACTED)

EVIDENCE_KINDS = (
    "SYNTHETIC_PRIMARY_SOURCE",
    "SYNTHETIC_SECONDARY_SOURCE",
    "SYNTHETIC_NUMERIC_CHECK",
    "SYNTHETIC_TIMELINE_CHECK",
    "SYNTHETIC_POLICY_CONTEXT",
)
PROVENANCE_KINDS = ("FIXTURE", "FUTURE_EXTERNAL_SOURCE_REQUIRED")

REVISION_REASONS = (
    "SUPPORTING_EVIDENCE_RECEIVED",
    "CONTRADICTING_EVIDENCE_RECEIVED",
    "INSUFFICIENT_EVIDENCE",
    "RETRACTION_REQUIRED",
    "CONFLICT_REOPENED",
)
CONTRADICTION_STATUSES = ("OPEN", "REQUIRES_MORE_EVIDENCE", "RETRACTION_RECOMMENDED")

# Doctrine / boundary statements.
MODEL_OUTPUT_IS_NOT_EVIDENCE = "A model output is not evidence."
VERIFICATION_TASK_IS_NOT_EVIDENCE = "A verification task is not evidence."
BELIEF_STATE_IS_NOT_TRUTH = "A belief state is not truth."
BELIEF_REVISION_IS_NOT_CERTAINTY = "A belief revision is not certainty."
EVIDENCE_MUST_CARRY_PROVENANCE = "Evidence must carry provenance."
NO_PROVENANCE_NO_PROMOTION = "A belief without provenance must not be promoted."
CONTRADICTION_CREATES_PATH = "A contradiction must create a revision or retraction path, not be hidden."


class BeliefRevisionError(ValueError):
    """WMBR-03 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "truth_claimed": False,
        "certainty_claimed": False,
        "claim_marked_true": False,
        "claim_marked_false": False,
        "model_output_is_evidence": False,
        "model_output_treated_as_evidence": False,
        "model_consensus_treated_as_evidence": False,
        "verification_task_treated_as_evidence": False,
        "belief_state_treated_as_truth": False,
        "belief_revision_treated_as_certainty": False,
        "truth_resolved": False,
        "contradictions_resolve_truth": False,
        "deletion_performed": False,
        "rewrite_performed": False,
        "original_claim_deleted_or_rewritten": False,
        "authority_granted": False,
        "tools_authorized": False,
        "tool_authorized": False,
        "external_call_made": False,
        "external_provider_call_made": False,
        "external_provider_calls_made": False,
        "web_browse_performed": False,
        "live_effects_created": False,
        "live_external_side_effects_created": False,
        "new_live_posts_created": False,
        "claims_agi": False,
        "candidate_agi_parent_phase_completed": False,
    }


FORBIDDEN_TRUE = {
    "truth_claimed": "truth_claimed",
    "certainty_claimed": "certainty_claimed",
    "claim_marked_true": "claim_marked_true",
    "claim_marked_false": "claim_marked_false",
    "model_output_is_evidence": "model_output_treated_as_evidence",
    "model_output_treated_as_evidence": "model_output_treated_as_evidence",
    "model_consensus_treated_as_evidence": "model_consensus_treated_as_evidence",
    "verification_task_treated_as_evidence": "verification_task_treated_as_evidence",
    "belief_state_treated_as_truth": "belief_state_treated_as_truth",
    "belief_revision_treated_as_certainty": "belief_revision_treated_as_certainty",
    "truth_resolved": "contradiction_resolved_truth",
    "contradictions_resolve_truth": "contradiction_resolved_truth",
    "deletion_performed": "original_claim_deleted",
    "rewrite_performed": "original_claim_rewritten",
    "original_claim_deleted_or_rewritten": "original_claim_deleted_or_rewritten",
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "tool_authorized": "tool_authorized",
    "external_call_made": "external_call_made",
    "external_provider_call_made": "external_provider_call",
    "external_provider_calls_made": "external_provider_call",
    "web_browse_performed": "web_browse",
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
            raise BeliefRevisionError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
