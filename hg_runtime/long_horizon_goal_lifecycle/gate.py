"""LHRE-01 / CAGI-54 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.long_horizon_goal_lifecycle.schemas import VERDICT_RED


def validate_lhre01_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "aec06_green": "aec06_not_green",
        "goals_written": "goals_required",
        "milestones_written": "milestones_required",
        "checkpoints_written": "checkpoints_required",
        "pause_resume_recorded": "pause_resume_required",
        "all_goals_valid": "goals_must_be_valid",
        "no_deployment_claims": "no_deployment_claims_allowed",
        "state_mutation_detected": "mutation_detection_required",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_goal_authority_tripwire": "reject_authority_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_goal_authority_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "action_authorized",
        "authority_granted",
        "tool_authorized",
        "live_effect_created",
        "agi_claimed",
        "deployment_claimed",
        "goal_treated_as_permission",
        "milestone_treated_as_deployment",
        "checkpoint_treated_as_authorization",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)

    if result.get("goal_count", 0) < 1:
        failures.append("goals_required")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
