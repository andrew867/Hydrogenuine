"""LHRE-06 / CAGI-59 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.long_horizon_reliability_consolidation.schemas import VERDICT_RED


def validate_lhre06_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "lhre05_green": "lhre05_not_green",
        "all_lhre_phases_green": "all_phases_must_be_green",
        "tranche_summary_valid": "summary_required",
        "gate_chain_verified": "gate_chain_required",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_consolidation_authority_tripwire": "reject_consolidation_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_consolidation_authority_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "deployment_certified", "tool_authorized", "authority_granted",
        "live_effect_created", "agi_claimed", "tranche_treated_as_agi",
        "web_browse_performed", "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
