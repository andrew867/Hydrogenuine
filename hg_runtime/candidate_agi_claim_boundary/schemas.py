"""P71 candidate-AGI claim boundary schemas."""

from __future__ import annotations

PHASE_ID = "P71"
VERDICT_GREEN = "GREEN_P71_CANDIDATE_AGI_CLAIM_BOUNDARY_FINAL_CONSOLIDATION"
VERDICT_YELLOW = "YELLOW_P71_CLAIM_BOUNDARY_PARTIAL"
VERDICT_RED = "RED_P71_CLAIM_BOUNDARY_FAILED"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

ALLOWED_CLAIMS = frozenset({
    "governed_agent_runtime",
    "candidate_agi_roadmap_implementation_substrate",
    "fixture_mode_local_mode_proofed_components",
    "simulated_economic_work_only",
    "local_inference_boundary_exists",
    "state_space_memory_organ_exists",
    "simulated_work_capsule_exists",
    "docker_fixture_mode_exists",
    "no_live_field_trial_authorization",
})

PROHIBITED_CLAIMS = frozenset({
    "agi",
    "conscious",
    "sentient",
    "sovereign",
    "self_authorizing",
    "deployed",
    "production_ready",
    "live_field_trial_complete",
    "live_social_media_capable_by_default",
    "real_customer_work_capable_by_default",
    "real_economic_work_complete",
    "external_provider_enabled_by_default",
    "phase19_green",
    "phase24_full_overnight_green",
})


class ClaimBoundaryError(Exception):
    pass


def reject_prohibited_claim(payload: dict) -> None:
    for key in (
        "claims_agi",
        "claims_consciousness",
        "claims_sentience",
        "claims_sovereignty",
        "claims_self_authorization",
        "claims_deployed",
        "claims_production_ready",
        "claims_field_trial_success",
        "claims_live_provider_enabled",
        "claims_real_economic_work",
        "claims_real_customer_work",
        "phase19_green_claimed",
        "phase24_full_overnight_green_claimed",
        "deployment_permission_claimed",
        "live_field_trial_authorized",
        "tool_authorized",
        "live_effect_created",
        "authority_mutated",
        "patch_applied",
        "hg_local_touched",
        "web_browse_performed",
        "external_provider_enabled",
    ):
        if payload.get(key):
            raise ClaimBoundaryError(
                f"Claim boundary violation: {key} must not be truthy"
            )
