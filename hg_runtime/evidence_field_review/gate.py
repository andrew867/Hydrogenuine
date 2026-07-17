"""P70 evidence field review gate."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.evidence_field_review.schemas import VERDICT_RED


def validate_p70_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for key, msg in {
        "reproduction_packet_exists": "packet_required",
        "evidence_review_exists": "review_required",
        "reviewer_notes_exist": "notes_required",
        "fixture_shadow_mode": "fixture_mode_required",
        "discrepancy_preserved": "discrepancy_preservation",
        "unresolved_gap_preserved": "gap_preservation",
        "reproduction_not_truth": "reproduction_not_truth",
        "reproduction_not_deployment": "reproduction_not_deployment",
        "reviewer_not_authority": "reviewer_not_authority",
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
        "reproduction_treated_as_truth", "reviewer_note_treated_as_authority",
        "reproduction_is_deployment_permission", "live_trial_authorized",
        "live_effect_created", "tool_authorized", "external_provider_enabled",
        "discrepancy_suppressed", "unresolved_gap_suppressed",
        "claims_agi", "claims_consciousness", "claims_sovereignty",
        "phase19_green_claimed", "phase24_full_overnight_green_claimed",
        "hg_local_touched", "web_browse_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
