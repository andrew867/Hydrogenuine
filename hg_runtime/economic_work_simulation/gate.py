"""SIEW-01 / CAGI-63 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.economic_work_simulation.schemas import VERDICT_RED


def validate_siew01_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "bsi03_green": "bsi03_not_green",
        "tasks_written": "tasks_required",
        "artifacts_written": "artifacts_required",
        "all_tasks_valid": "tasks_must_be_valid",
        "all_artifacts_valid": "artifacts_must_be_valid",
        "all_simulated": "all_must_be_simulated",
        "no_real_customers": "no_real_customers_required",
        "no_real_payments": "no_real_payments_required",
        "value_advisory_only": "value_must_be_advisory",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_real_economic_work_tripwire": "reject_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_real_work_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "real_customer_served", "real_payment_processed", "money_moved",
        "invoice_created", "tool_authorized", "tool_executed",
        "external_contact_made", "web_call_made", "provider_call_made",
        "live_submission_made", "deployment_claimed", "agi_claimed",
        "web_browse_performed", "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
