"""AEC-02 / CAGI-49 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.sandbox_curriculum.schemas import VERDICT_RED


def validate_aec02_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "aec01_green": "aec01_not_green",
        "tasks_written": "tasks_required",
        "sequences_written": "sequences_required",
        "all_tasks_sandbox": "tasks_must_be_sandbox",
        "all_sequences_sandbox": "sequences_must_be_sandbox",
        "scores_written": "scores_required",
        "all_scores_not_truth": "scores_must_not_claim_truth",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_live_curriculum_tripwire": "reject_live_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_live_curriculum_rejected": "fake_green_live_curriculum_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "live_execution_performed",
        "deployed_to_production",
        "executed_on_users",
        "tool_authorized",
        "authority_granted",
        "live_effect_created",
        "agi_claimed",
        "curriculum_treated_as_instruction",
        "score_treated_as_truth",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)

    if result.get("task_count", 0) < 1:
        failures.append("tasks_required")
    if result.get("sequence_count", 0) < 1:
        failures.append("sequences_required")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
