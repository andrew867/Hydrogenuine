"""P71 candidate-AGI claim boundary gate."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.candidate_agi_claim_boundary.schemas import VERDICT_RED


def validate_p71_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for key, msg in {
        "capability_matrix_exists": "matrix_required",
        "extension_matrix_exists": "ext_matrix_required",
        "known_debt_register_exists": "debt_required",
        "claim_boundary_exists": "claim_boundary_required",
        "allowed_claim_summary_exists": "allowed_claims_required",
        "public_safe_summary_exists": "public_summary_required",
        "final_evidence_inventory_exists": "evidence_inventory_required",
        "final_soak_readiness_exists": "soak_readiness_required",
        "no_agi_claim": "agi_claim_rejected",
        "no_consciousness_claim": "consciousness_claim_rejected",
        "no_sovereignty_claim": "sovereignty_claim_rejected",
        "no_self_authorization_claim": "self_auth_claim_rejected",
        "no_deployment_claim": "deployment_claim_rejected",
        "no_field_trial_success_claim": "field_trial_claim_rejected",
        "no_live_provider_claim": "provider_claim_rejected",
        "no_real_economic_work_claim": "economic_work_claim_rejected",
        "known_debt_preserved": "debt_must_be_preserved",
        "phase19_yellow_preserved": "phase19",
        "phase24_infrastructure_only_preserved": "phase24",
        "replay_preserves_hashes": "replay",
        "proof_bundle_valid": "proof",
        "report_present": "report",
        "fake_green_rejected": "fake_green",
        "secret_scan_clean": "secret_scan",
    }.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "claims_agi", "claims_consciousness", "claims_sentience",
        "claims_sovereignty", "claims_self_authorization",
        "claims_deployed", "claims_production_ready",
        "claims_field_trial_success", "claims_live_provider_enabled",
        "claims_real_economic_work", "claims_real_customer_work",
        "phase19_green_claimed", "phase24_full_overnight_green_claimed",
        "deployment_permission_claimed", "live_field_trial_authorized",
        "tool_authorized", "live_effect_created", "authority_mutated",
        "hg_local_touched", "web_browse_performed", "external_provider_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
