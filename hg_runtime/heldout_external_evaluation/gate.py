"""LHRE-04 / CAGI-57 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.heldout_external_evaluation.schemas import VERDICT_RED


def validate_lhre04_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "lhre03_green": "lhre03_not_green",
        "heldout_tasks_written": "heldout_tasks_required",
        "attempts_written": "attempts_required",
        "leakage_checks_passed": "leakage_checks_required",
        "all_tasks_heldout": "tasks_must_be_heldout",
        "no_leakage_detected": "no_leakage_allowed",
        "all_attempts_valid": "attempts_must_be_valid",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_heldout_authority_tripwire": "reject_heldout_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_heldout_authority_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "leaked_to_curriculum", "live_external_call_made",
        "tool_authorized", "authority_granted", "live_effect_created",
        "agi_claimed", "deployment_claimed", "score_treated_as_competence",
        "web_browse_performed", "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
