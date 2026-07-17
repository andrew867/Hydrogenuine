"""SIEW-03 / CAGI-65 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.self_improvement_economic_consolidation.schemas import VERDICT_RED


def validate_siew03_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "siew02_green": "siew02_not_green",
        "p60_receipt_green": "p60_not_green",
        "p61_receipt_green": "p61_not_green",
        "p62_receipt_green": "p62_not_green",
        "p63_receipt_green": "p63_not_green",
        "p64_receipt_green": "p64_not_green",
        "all_receipts_aggregated": "receipts_required",
        "proposal_task_links_present": "links_required",
        "advisory_performance_delta_recorded": "delta_required",
        "self_improvement_advisory": "self_improvement_must_be_advisory",
        "economic_work_simulated": "economic_work_must_be_simulated",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_consolidation_overreach_tripwire": "reject_tripwire_required",
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
        "patch_applied", "authority_mutated", "customer_work_performed",
        "money_moved", "tool_authorized", "deployment_permission_granted",
        "live_effect_created", "agi_claimed", "self_modification_applied",
        "provider_enabled",
        "web_browse_performed", "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
