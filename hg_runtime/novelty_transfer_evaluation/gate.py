"""AEC-03 / CAGI-50 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.novelty_transfer_evaluation.schemas import VERDICT_RED


def validate_aec03_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "aec02_green": "aec02_not_green",
        "baseline_scores_present": "baseline_required",
        "novelty_tasks_present": "novelty_tasks_required",
        "transfer_scores_present": "transfer_scores_required",
        "all_scores_not_truth": "scores_must_not_claim_truth",
        "no_live_evaluation": "no_live_evaluation_allowed",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_live_transfer_tripwire": "reject_live_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_live_transfer_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "live_evaluation_performed",
        "live_execution_performed",
        "deployed_to_production",
        "tool_authorized",
        "authority_granted",
        "live_effect_created",
        "agi_claimed",
        "transfer_treated_as_capability",
        "score_treated_as_truth",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
