"""Local Inference QA Orchestrator gate."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.local_inference_qa_orchestrator.schemas import VERDICT_RED


def validate_qa_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for key, msg in {
        "qa_complete": "qa_required",
        "receipts_present": "receipts_required",
        "non_truth_boundary": "non_truth_required",
        "no_patch_application": "no_patch_required",
        "no_tool_authorization": "no_tool_auth_required",
        "replay_preserves_hashes": "replay_required",
        "proof_bundle_valid": "proof_required",
        "report_present": "report_required",
        "phase19_yellow_preserved": "phase19",
        "phase24_infrastructure_only_preserved": "phase24",
        "secret_scan_clean": "secret_scan",
    }.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "live_effect", "tool_authorized", "external_provider_enabled",
        "claims_agi", "claims_consciousness", "claims_sovereignty",
        "deployment_permission_claimed", "live_field_trial_authorized",
        "phase19_green_claimed", "phase24_full_overnight_green_claimed",
        "hg_local_touched", "web_browse_performed",
        "patch_applied", "test_created_from_model_output",
        "green_inferred_from_model_output",
        "recommendation_is_permission", "output_is_truth",
    ):
        if result.get(key):
            failures.append(key)
    return {
        "ok": not failures and result.get("verdict") != VERDICT_RED,
        "failures": failures,
    }
