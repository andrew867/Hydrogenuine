"""P69 field trial readiness boundary gate."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.field_trial_readiness_boundary.schemas import VERDICT_RED


def validate_p69_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for key, msg in {
        "checklist_exists": "checklist_required",
        "scenario_exists": "scenario_required",
        "rehearsal_exists": "rehearsal_required",
        "live_effect_inventory_exists": "inventory_required",
        "readiness_gap_exists": "gap_required",
        "operator_approval_required": "operator_approval_required",
        "field_readiness_not_live_trial": "readiness_not_trial",
        "rehearsal_not_live_trial": "rehearsal_not_trial",
        "readiness_not_deployment_permission": "not_deployment",
        "no_live_effects": "no_live_effects",
        "no_tool_authorization": "no_tool_auth",
        "no_external_providers": "no_providers",
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
        "live_field_trial_authorized", "deployment_permission_claimed",
        "live_effect_created", "tool_authorized", "external_provider_enabled",
        "claims_agi", "claims_consciousness", "claims_sovereignty",
        "phase19_green_claimed", "phase24_full_overnight_green_claimed",
        "hg_local_touched", "web_browse_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
