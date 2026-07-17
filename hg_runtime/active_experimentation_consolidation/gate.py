"""AEC-06 / CAGI-53 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.active_experimentation_consolidation.schemas import VERDICT_RED


def validate_aec06_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "aec01_through_aec05_green": "not_all_phases_green",
        "integration_checks_passed": "integration_checks_required",
        "tranche_summary_present": "tranche_summary_required",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_completion_claim_tripwire": "reject_completion_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_completion_claim_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "candidate_agi_complete",
        "deployment_ready",
        "live_execution_performed",
        "tool_authorized",
        "authority_granted",
        "live_effect_created",
        "agi_claimed",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
