"""AEC-04 / CAGI-51 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.experiment_proposal.schemas import VERDICT_RED


def validate_aec04_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "aec03_green": "aec03_not_green",
        "proposals_written": "proposals_required",
        "reviews_written": "reviews_required",
        "all_proposals_draft": "proposals_must_be_draft",
        "all_reviews_not_decision": "reviews_must_not_be_decision",
        "no_approvals_granted": "no_approvals_allowed",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_live_proposal_tripwire": "reject_live_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_approved_proposal_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "proposal_approved_for_execution",
        "live_execution_performed",
        "deployed_to_production",
        "tool_authorized",
        "authority_granted",
        "live_effect_created",
        "agi_claimed",
        "proposal_treated_as_approval",
        "review_treated_as_decision",
        "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)

    if result.get("proposal_count", 0) < 1:
        failures.append("proposals_required")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
