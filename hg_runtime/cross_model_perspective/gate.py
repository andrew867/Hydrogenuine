"""WMBR-01A / CAGI-42A gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.cross_model_perspective.schemas import VERDICT_RED


def validate_wmbr01a_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    # Required-true presence/boundary checks.
    checks = {
        "runtime_p42_green": "runtime_p42_not_green",
        "crosswalk_exists": "runtime_candidate_crosswalk_missing",
        "runtime_p42_declared_not_cagi42": "runtime_p42_cagi42_boundary_missing",
        "wmbr01a_declared_not_wmbr01": "wmbr01a_wmbr01_boundary_missing",
        "input_receipts_loaded": "input_receipts_required",
        "perspective_matrix_written": "perspective_matrix_required",
        "divergence_matrix_written": "divergence_matrix_required",
        "refusal_patterns_written": "refusal_patterns_required",
        "omission_patterns_written": "omission_patterns_required",
        "framing_signatures_written": "framing_signatures_required",
        "moral_consensus_matrix_written": "moral_consensus_matrix_required",
        "evidence_gap_tasks_written": "evidence_gap_tasks_required",
        "every_matrix_cell_links_to_receipt": "matrix_cell_receipt_link_required",
        "consensus_is_explicitly_non_truth": "consensus_non_truth_required",
        "divergence_is_explicitly_non_evidence": "divergence_non_evidence_required",
        "refusal_is_explicitly_non_authority": "refusal_non_authority_required",
        "willingness_is_explicitly_non_permission": "willingness_non_permission_required",
        "moral_consensus_is_explicitly_non_authority": "moral_consensus_non_authority_required",
        "evidence_gap_tasks_are_not_actions": "evidence_gap_tasks_must_be_non_actions",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase40_repair_preserved": "phase40_repair_not_preserved",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_matrix_hashes": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_truth_claim_rejected": "fake_green_truth_claim_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    # Forbidden-true flags.
    for key in (
        "external_provider_calls_made",
        "model_output_treated_as_truth",
        "model_consensus_treated_as_truth",
        "model_disagreement_treated_as_evidence",
        "model_refusal_treated_as_authority",
        "model_willingness_treated_as_permission",
        "moral_consensus_treated_as_authority",
        "moral_claim_treated_as_authority",
        "evidence_gap_tasks_authorize_actions",
        "tools_authorized",
        "authority_granted",
        "live_external_side_effects_created",
        "new_live_posts_created",
        "large_30b_model_loaded",
        "security_model_used",
        "deepseek_model_used",
    ):
        if result.get(key):
            failures.append(key)

    # WMBR-01A must not claim completion of its parent phase.
    if result.get("candidate_agi_parent_phase_completed"):
        failures.append("candidate_agi_parent_phase_completion_claim")

    if result.get("participant_count", 0) < 3 or result.get("receipt_count", 0) < 3:
        failures.append("insufficient_cross_model_receipts")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
