"""Phase 42 provider portability schemas and boundaries."""

from __future__ import annotations

from typing import Any, Mapping

MODEL_PARTICIPANT_SCHEMA = "model_participant_v1"
PROVIDER_ADAPTER_SCHEMA = "provider_adapter_v1"
PROVIDER_CAPABILITY_SCHEMA = "provider_capability_v1"
CROSS_MODEL_PROMPT_SCHEMA = "cross_model_prompt_v1"
MODEL_RESPONSE_RECEIPT_SCHEMA = "model_response_receipt_v1"
MODEL_REFUSAL_RECORD_SCHEMA = "model_refusal_record_v1"
MODEL_WILLINGNESS_RECORD_SCHEMA = "model_willingness_record_v1"
FRAMING_SIGNAL_SCHEMA = "response_framing_signal_v1"
OMISSION_SIGNAL_SCHEMA = "response_omission_signal_v1"
MORAL_PRINCIPLE_SIGNAL_SCHEMA = "moral_principle_signal_v1"
EVIDENCE_GAP_SIGNAL_SCHEMA = "evidence_gap_signal_v1"
TOKEN_COST_ESTIMATE_SCHEMA = "token_cost_estimate_v1"
CROSS_MODEL_RUN_MANIFEST_SCHEMA = "cross_model_run_manifest_v1"
CROSS_MODEL_RUN_SUMMARY_SCHEMA = "cross_model_run_summary_v1"
CROSS_MODEL_REPLAY_RECORD_SCHEMA = "cross_model_replay_record_v1"
GATE_RESULT_SCHEMA = "provider_portability_gate_result_v1"

VERDICT_GREEN = "GREEN_PHASE42_PROVIDER_PORTABILITY_CROSS_MODEL_RECEIPT_SUBSTRATE"
VERDICT_YELLOW = "YELLOW_PHASE42_PROVIDER_PORTABILITY_PARTIAL"
VERDICT_RED = "RED_PHASE42_PROVIDER_PORTABILITY_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"
DOCTRINE = "Every model is a compressed civilization artifact."


class ProviderPortabilityError(ValueError):
    """Phase 42 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
        "external_provider_call_made": False,
        "external_provider_calls_made": False,
        "model_output_treated_as_truth": False,
        "model_consensus_treated_as_truth": False,
        "model_disagreement_treated_as_evidence": False,
        "model_refusal_treated_as_authority": False,
        "model_willingness_treated_as_permission": False,
        "moral_claim_treated_as_authority": False,
        "new_live_posts_created": False,
        "claims_agi": False,
    }


FORBIDDEN_TRUE = {
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "live_effects_created": "live_effect_created",
    "external_provider_call_made": "external_provider_call",
    "external_provider_calls_made": "external_provider_call",
    "model_output_treated_as_truth": "model_output_treated_as_truth",
    "model_consensus_treated_as_truth": "model_consensus_treated_as_truth",
    "model_disagreement_treated_as_evidence": "model_disagreement_treated_as_evidence",
    "model_refusal_treated_as_authority": "model_refusal_treated_as_authority",
    "model_willingness_treated_as_permission": "model_willingness_treated_as_permission",
    "moral_claim_treated_as_authority": "moral_claim_treated_as_authority",
    "new_live_posts_created": "live_post_created",
    "claims_agi": "claims_agi_forbidden",
}


def assert_neutral(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if value and str(key) in FORBIDDEN_TRUE:
            raise ProviderPortabilityError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
