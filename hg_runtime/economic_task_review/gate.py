"""SIEW-02 / CAGI-64 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.economic_task_review.schemas import VERDICT_RED


def validate_siew02_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "siew01_green": "siew01_not_green",
        "reviews_written": "reviews_required",
        "criteria_written": "criteria_required",
        "all_reviews_valid": "reviews_must_be_valid",
        "no_customer_acceptance": "no_customer_acceptance_required",
        "no_payment_permission": "no_payment_permission_required",
        "all_require_operator_review": "operator_review_required",
        "defects_recorded": "defect_recording_required",
        "uncertainty_recorded": "uncertainty_recording_required",
        "receipt_chain_present": "receipt_chain_required",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_real_acceptance_tripwire": "reject_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_real_acceptance_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "customer_accepted", "payment_permitted", "invoice_sent",
        "live_submitted", "tool_authorized", "external_action_taken",
        "money_moved", "deployment_claimed", "agi_claimed",
        "web_browse_performed", "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
