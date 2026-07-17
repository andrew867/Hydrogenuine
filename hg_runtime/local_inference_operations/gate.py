"""CLIFT-03 / CAGI-68 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.local_inference_operations.schemas import VERDICT_RED


def validate_clift03_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "model_registry_recorded": "registry_required",
        "resource_estimate_recorded": "resource_estimate_required",
        "oversized_model_refused": "oversized_refusal_required",
        "large_model_default_refused": "large_default_refusal_required",
        "provider_disabled_by_default": "provider_disabled_required",
        "output_non_truth_boundary": "non_truth_boundary_required",
        "inference_not_authority": "inference_not_authority_required",
        "tool_authorization_refused": "tool_refused_required",
        "network_requirement_refused": "network_refused_required",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_inference_overreach_tripwire": "reject_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_overreach_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "inference_treated_as_authority",
        "output_treated_as_truth",
        "availability_treated_as_permission",
        "provider_enabled_by_default",
        "large_model_default_load",
        "network_required",
        "external_provider_call",
        "tool_authorized",
        "hg_local_accessed",
        "live_effect_created",
        "agi_claimed",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
