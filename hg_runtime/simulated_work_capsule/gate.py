"""F12A simulated work capsule gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.simulated_work_capsule.schemas import VERDICT_RED


def validate_f12a_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    required_true = {
        "capsule_task_exists": "capsule_task_required",
        "work_plan_exists": "work_plan_required",
        "artifact_exists": "artifact_required",
        "review_packet_exists": "review_packet_required",
        "soak_workload_exists": "soak_workload_required",
        "f02_memory_ref_exists": "f02_ref_required",
        "capsule_simulated_only": "capsule_must_be_simulated",
        "no_customer_contact": "no_customer_contact_required",
        "no_live_posting": "no_posting_required",
        "no_message_send": "no_message_required",
        "no_payment": "no_payment_required",
        "no_money_movement": "no_money_required",
        "no_invoice": "no_invoice_required",
        "no_tool_authorization": "no_tool_auth_required",
        "no_patch_application": "no_patch_required",
        "no_authority_mutation": "no_auth_mutation_required",
        "no_live_provider": "no_live_provider_required",
        "no_live_effects": "no_live_effects_required",
        "no_hg_local": "no_hg_local_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infra",
        "replay_preserves_hashes": "replay_required",
        "proof_bundle_valid": "proof_required",
        "report_present": "report_required",
        "fake_green_rejected": "fake_green_required",
        "secret_scan_clean": "secret_scan_required",
        "p63_ref_exists": "p63_ref_required",
        "p64_ref_exists": "p64_ref_required",
        "p65_ref_exists": "p65_ref_required",
        "review_not_customer_acceptance": "review_not_acceptance",
        "value_not_payment_permission": "value_not_permission",
    }
    for key, msg in required_true.items():
        if not result.get(key):
            failures.append(msg)

    forbidden = (
        "real_customer",
        "customer_contact",
        "social_post_published",
        "message_sent",
        "real_payment",
        "money_movement",
        "invoice_created",
        "tool_authorized",
        "tool_executed",
        "patch_applied",
        "authority_mutated",
        "live_effect",
        "live_provider_enabled",
        "live_submission",
        "hg_local_touched",
        "deployment_claim",
        "claims_agi",
        "phase19_green_claimed",
        "phase24_full_overnight_green_claimed",
        "web_browse_performed",
        "external_provider_call",
    )
    for key in forbidden:
        if result.get(key):
            failures.append(key)

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
