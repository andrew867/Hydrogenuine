"""WMBR-04 / CAGI-45 causal-world-model-boundary schemas and boundaries."""

from __future__ import annotations

from typing import Any, Mapping

CAUSAL_CLAIM_RECORD_SCHEMA = "causal_claim_record_v1"
CAUSAL_HYPOTHESIS_RECORD_SCHEMA = "causal_hypothesis_record_v1"
CAUSAL_EDGE_RECORD_SCHEMA = "causal_edge_record_v1"
MECHANISM_PROPOSAL_SCHEMA = "mechanism_proposal_v1"
PREDICTION_RECORD_SCHEMA = "prediction_record_v1"
INTERVENTION_PROPOSAL_SCHEMA = "intervention_proposal_v1"
FALSIFICATION_CONDITION_SCHEMA = "falsification_condition_v1"
GRAPH_MANIFEST_SCHEMA = "causal_graph_manifest_v1"
REPLAY_RECORD_SCHEMA = "causal_world_model_replay_record_v1"
GATE_RESULT_SCHEMA = "wmbr_04_gate_result_v1"

PHASE_ID = "WMBR-04"
LEGACY_PHASE_ID = "CAGI-45"
PARENT_PHASE_ID = "WMBR-01"
LEGACY_PARENT_PHASE_ID = "CAGI-42"
SOURCE_PHASE_ID = "WMBR-03"
SOURCE_LEGACY_PHASE_ID = "CAGI-44"

VERDICT_GREEN = "GREEN_WMBR_04_CAUSAL_WORLD_MODEL_BOUNDARY"
VERDICT_YELLOW = "YELLOW_WMBR_04_CAUSAL_BOUNDARY_PARTIAL"
VERDICT_RED = "RED_WMBR_04_CAUSAL_BOUNDARY_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
WMBR_03_VERDICT_GREEN = "GREEN_WMBR_03_BELIEF_REVISION_LEDGER"
WMBR_02_VERDICT_GREEN = "GREEN_WMBR_02_BELIEF_CONFLICT_VERIFICATION_QUEUE"
WMBR_01A_VERDICT_GREEN = "GREEN_WMBR_01A_CROSS_MODEL_PERSPECTIVE_MATRIX"
RUNTIME_P42_VERDICT_GREEN = "GREEN_PHASE42_PROVIDER_PORTABILITY_CROSS_MODEL_RECEIPT_SUBSTRATE"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
DOCTRINE = "Every model is a compressed civilization artifact."

# Belief statuses (from WMBR-03) that are provenance-bound seeds.
SEED_BELIEF_STATUSES = ("PROVISIONALLY_SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE")
# Belief statuses that must NOT seed active hypotheses.
NON_SEED_BELIEF_STATUSES = ("UNVERIFIED", "RETRACTED")

HYPOTHESIS_STATUSES = ("PROPOSED", "INSUFFICIENT_EVIDENCE", "CONTRADICTED", "RETRACTED", "NEEDS_TEST")
BELIEF_TO_HYPOTHESIS_STATUS = {
    "PROVISIONALLY_SUPPORTED": "PROPOSED",
    "CONTRADICTED": "CONTRADICTED",
    "INSUFFICIENT_EVIDENCE": "INSUFFICIENT_EVIDENCE",
}

RELATION_TYPES = (
    "CAUSES_HYPOTHESIZED",
    "ENABLES_HYPOTHESIZED",
    "INHIBITS_HYPOTHESIZED",
    "CORRELATES_WITH",
    "MECHANISM_PROPOSED",
)
EDGE_STATUSES = ("HYPOTHETICAL", "CONTRADICTED", "INSUFFICIENT_EVIDENCE")
UNCERTAINTY_LEVELS = ("HIGH", "MEDIUM", "LOW")

# Doctrine / boundary statements.
BELIEF_STATE_IS_NOT_TRUTH = "A belief state is not truth."
BELIEF_REVISION_IS_NOT_CERTAINTY = "A belief revision is not certainty."
CAUSAL_HYPOTHESIS_IS_NOT_TRUTH = "A causal hypothesis is not causal truth."
CORRELATION_IS_NOT_CAUSATION = "Correlation is not causation."
MECHANISM_IS_NOT_PROOF = "A mechanism proposal is not proof."
PREDICTION_IS_NOT_VERIFICATION = "A prediction is not verification."
INTERVENTION_IS_NOT_ACTION = "An intervention proposal is not an action."
FALSIFICATION_IS_NOT_AUTHORITY = "A falsification condition is not execution authority."
EVIDENCE_MUST_CARRY_PROVENANCE = "Evidence must carry provenance."
CONTRADICTION_STAYS_VISIBLE = "Contradictory evidence must remain visible."


class CausalBoundaryError(ValueError):
    """WMBR-04 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "truth_claimed": False,
        "certainty_claimed": False,
        "causal_truth_claimed": False,
        "causality_claimed_as_fact": False,
        "belief_state_treated_as_truth": False,
        "belief_revision_treated_as_certainty": False,
        "causal_hypothesis_treated_as_truth": False,
        "causal_edge_treated_as_truth": False,
        "edge_is_truth": False,
        "correlation_is_causation": False,
        "correlation_treated_as_causation": False,
        "mechanism_is_proof": False,
        "mechanism_proposal_treated_as_proof": False,
        "prediction_is_verification": False,
        "prediction_treated_as_verification": False,
        "intervention_authorized": False,
        "intervention_proposal_treated_as_action": False,
        "action_authorized": False,
        "external_test_authorized": False,
        "execution_authorized": False,
        "falsification_condition_treated_as_execution_authority": False,
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
    "causal_truth_claimed": "causal_truth_claimed",
    "causality_claimed_as_fact": "causality_claimed_as_fact",
    "belief_state_treated_as_truth": "belief_state_treated_as_truth",
    "belief_revision_treated_as_certainty": "belief_revision_treated_as_certainty",
    "causal_hypothesis_treated_as_truth": "causal_hypothesis_treated_as_truth",
    "causal_edge_treated_as_truth": "causal_edge_treated_as_truth",
    "edge_is_truth": "causal_edge_treated_as_truth",
    "correlation_is_causation": "correlation_treated_as_causation",
    "correlation_treated_as_causation": "correlation_treated_as_causation",
    "mechanism_is_proof": "mechanism_proposal_treated_as_proof",
    "mechanism_proposal_treated_as_proof": "mechanism_proposal_treated_as_proof",
    "prediction_is_verification": "prediction_treated_as_verification",
    "prediction_treated_as_verification": "prediction_treated_as_verification",
    "intervention_authorized": "intervention_authorized",
    "intervention_proposal_treated_as_action": "intervention_proposal_treated_as_action",
    "action_authorized": "action_authorized",
    "external_test_authorized": "external_test_authorized",
    "execution_authorized": "execution_authorized",
    "falsification_condition_treated_as_execution_authority": "falsification_condition_treated_as_execution_authority",
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
            raise CausalBoundaryError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
