"""AEC-05 / CAGI-52 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.curriculum_failure_review.schemas import VERDICT_RED


def validate_aec05_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "aec04_green": "aec04_not_green",
        "failures_written": "failures_required",
        "root_causes_written": "root_causes_required",
        "reviews_written": "reviews_required",
        "all_failures_queued": "failures_must_be_queued",
        "all_causes_hypothesis": "causes_must_be_hypothesis",
        "no_fixes_applied": "no_fixes_allowed",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_live_failure_action_tripwire": "reject_live_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_fix_applied_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "fix_applied",
        "patch_deployed",
        "live_execution_performed",
        "tool_authorized",
        "authority_granted",
        "live_effect_created",
        "agi_claimed",
        "failure_treated_as_defect",
        "review_treated_as_fix",
        "root_cause_treated_as_diagnosis",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)

    if result.get("failure_count", 0) < 1:
        failures.append("failures_required")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
