"""WMBR-03 / CAGI-44 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.belief_revision_ledger.schemas import VERDICT_RED


def validate_wmbr03_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "wmbr02_green": "wmbr02_not_green",
        "wmbr01a_green": "wmbr01a_not_green",
        "runtime_p42_green": "runtime_p42_not_green",
        "input_queue_loaded": "input_queue_required",
        "candidate_claims_loaded": "candidate_claims_required",
        "evidence_receipts_written": "evidence_receipts_required",
        "all_evidence_has_provenance": "evidence_receipts_must_have_provenance",
        "belief_states_written": "belief_states_required",
        "belief_revisions_written": "belief_revisions_required",
        "provenance_chains_written": "provenance_chains_required",
        "provenance_chain_required_for_promoted_state": "promoted_state_missing_provenance",
        "supporting_evidence_only_provisional": "supporting_evidence_over_promoted",
        "contradiction_records_written": "contradiction_records_required",
        "retraction_preserves_original_claim": "retraction_must_preserve_original_claim",
        "unsupported_claims_remain_unverified": "unsupported_claims_must_remain_unverified",
        "model_output_is_not_evidence": "model_output_must_not_be_evidence",
        "verification_task_is_not_evidence": "verification_task_must_not_be_evidence",
        "belief_state_is_not_truth": "belief_state_must_not_be_truth",
        "belief_revision_is_not_certainty": "belief_revision_must_not_be_certainty",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase40_repair_preserved": "phase40_repair_not_preserved",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_revision_hashes": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_truth_revision_rejected": "fake_green_truth_revision_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)

    for key in (
        "claims_marked_true",
        "claims_marked_false",
        "certainty_claimed",
        "truth_claimed",
        "model_output_treated_as_evidence",
        "model_consensus_treated_as_evidence",
        "verification_task_treated_as_evidence",
        "belief_state_treated_as_truth",
        "belief_revision_treated_as_certainty",
        "contradictions_resolve_truth",
        "original_claim_deleted_or_rewritten",
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

    if result.get("evidence_receipt_count", 0) < 1:
        failures.append("evidence_receipts_required")
    if result.get("belief_state_count", 0) < 1:
        failures.append("belief_states_required")
    if result.get("belief_revision_count", 0) < 1:
        failures.append("belief_revisions_required")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
