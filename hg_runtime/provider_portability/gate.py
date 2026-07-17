"""Phase 42 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.provider_portability.schemas import VERDICT_RED


def validate_phase42_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures = []
    for phase in ("phase41", "phase40", "phase39", "phase38", "phase37", "phase35"):
        if not result.get(f"{phase}_green"):
            failures.append(f"phase42_gate_requires_{phase}_green")
    checks = {
        "fixture_participants_registered": "participants_missing",
        "cross_model_run_completed": "cross_model_run_missing",
        "model_response_receipts_written": "receipts_missing",
        "external_providers_disabled_by_default": "external_not_disabled",
        "token_cost_estimates_recorded": "token_cost_missing",
        "refusal_records_written": "refusal_records_missing",
        "willingness_records_written": "willingness_records_missing",
        "framing_signals_written": "framing_signals_missing",
        "moral_principle_signals_written": "moral_signals_missing",
        "evidence_gap_signals_written": "evidence_gaps_missing",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase40_repair_preserved": "phase40_repair_not_preserved",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_receipt_hashes": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_external_call_rejected": "fake_green_external_call_not_rejected",
        "crosswalk_exists": "runtime_candidate_crosswalk_missing",
        "runtime_p42_declared_not_cagi42": "runtime_p42_cagi42_boundary_missing",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in ("external_provider_calls_made", "model_output_treated_as_truth", "model_consensus_treated_as_truth", "model_disagreement_treated_as_evidence", "model_refusal_treated_as_authority", "model_willingness_treated_as_permission", "moral_claim_treated_as_authority", "authority_granted", "tools_authorized", "live_external_side_effects_created", "new_live_posts_created"):
        if result.get(key):
            failures.append(key)
    if result.get("candidate_agi_phase_completed") or result.get("candidate_agi_phase_ids_completed"):
        failures.append("candidate_agi_phase_completion_claim")
    if result.get("participant_count", 0) < 3 or result.get("receipt_count", 0) < 3:
        failures.append("insufficient_cross_model_receipts")
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
