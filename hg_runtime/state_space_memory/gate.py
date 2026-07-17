"""F02 state-space memory organ gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.state_space_memory.schemas import VERDICT_RED


def validate_f02_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "snapshots_exist": "snapshots_required",
        "transitions_exist": "transitions_required",
        "compressed_trajectory_exists": "trajectory_required",
        "repair_recommendations_exist": "recommendations_required",
        "compression_loss_declared": "compression_loss_required",
        "state_estimate_non_truth": "state_must_be_non_truth",
        "recall_non_authority": "recall_must_be_non_authority",
        "recommendations_non_permission": "recommendations_must_be_non_permission",
        "recommendations_non_patch_approval": "recommendations_must_be_non_patch",
        "no_tool_authorization": "tool_auth_must_be_rejected",
        "no_patch_application": "patch_app_must_be_rejected",
        "no_authority_mutation": "authority_mutation_must_be_rejected",
        "hash_chain_valid": "hash_chain_required",
        "replay_preserves_artifact_hash": "replay_required",
        "reject_memory_overreach_tripwire": "reject_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_rejected": "fake_green_must_be_rejected",
        "secret_scan_clean": "secret_scan_required",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "state_estimate_is_truth",
        "memory_is_evidence",
        "recall_is_authority",
        "state_prediction_is_permission",
        "recommendation_is_permission",
        "recommendation_is_patch_approval",
        "recommendation_authorizes_tools",
        "query_authorizes_actions",
        "memory_mutates_authority",
        "memory_marks_phase19_green",
        "memory_marks_phase24_full_overnight_green",
        "memory_enables_live_provider",
        "memory_creates_live_effect",
        "memory_touches_hg_local",
        "memory_applies_patch",
        "agi_claimed",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
