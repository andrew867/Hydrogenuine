"""WMBR-02 / CAGI-43 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.belief_verification_queue.schemas import VERDICT_RED


def validate_wmbr02_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "wmbr01a_green": "wmbr01a_not_green",
        "runtime_p42_green": "runtime_p42_not_green",
        "input_matrix_loaded": "input_matrix_required",
        "perspective_matrix_present": "perspective_matrix_required",
        "divergence_matrix_present": "divergence_matrix_required",
        "candidate_claims_written": "candidate_claims_required",
        "belief_conflicts_written": "belief_conflicts_required",
        "verification_tasks_written": "verification_tasks_required",
        "verification_queue_manifest_written": "verification_queue_manifest_required",
        "evidence_policy_receipts_written": "evidence_policy_receipts_required",
        "all_claims_unverified": "claims_must_be_unverified",
        "all_belief_status_not_promoted": "belief_must_not_be_promoted",
        "all_tasks_queued_not_authorized": "tasks_must_be_queued_not_authorized",
        "model_output_is_not_evidence": "model_output_must_not_be_evidence",
        "model_consensus_is_not_evidence": "model_consensus_must_not_be_evidence",
        "model_refusal_is_not_evidence": "model_refusal_must_not_be_evidence",
        "conflict_record_is_not_evidence": "conflict_record_must_not_be_evidence",
        "verification_task_is_not_action": "task_must_not_be_action",
        "source_request_is_not_external_call": "source_request_must_not_be_external_call",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase40_repair_preserved": "phase40_repair_not_preserved",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_queue_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_verified_truth_rejected": "fake_green_verified_truth_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "claims_marked_true",
        "claims_marked_false",
        "belief_promoted",
        "conflict_record_treated_as_evidence",
        "verification_task_treated_as_action",
        "source_request_treated_as_external_call",
        "model_output_treated_as_evidence",
        "model_consensus_treated_as_evidence",
        "model_refusal_treated_as_evidence",
        "verification_tasks_authorize_tools",
        "web_browse_performed",
        "external_provider_calls_made",
        "new_live_posts_created",
        "live_external_side_effects_created",
        "large_30b_model_loaded",
        "security_model_used",
        "deepseek_model_used",
        "authority_granted",
        "tools_authorized",
    ):
        if result.get(key):
            failures.append(key)

    if result.get("candidate_agi_parent_phase_completed"):
        failures.append("candidate_agi_parent_phase_completion_claim")

    if result.get("claim_count", 0) < 1:
        failures.append("candidate_claims_required")
    if result.get("conflict_count", 0) < 1:
        failures.append("belief_conflicts_required")
    if result.get("verification_task_count", 0) < 1:
        failures.append("verification_tasks_required")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
