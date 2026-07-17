"""Phase 36 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.autonomous_proposal_soak.schemas import VERDICT_GREEN_REPAIRED, VERDICT_RED, VERDICT_YELLOW_BACKLOG


def validate_phase36_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if result.get("external_provider_calls_made"):
        failures.append("external_provider_calls_forbidden")
    if result.get("live_external_side_effects_created"):
        failures.append("live_side_effects_forbidden")
    if result.get("large_30b_model_loaded") or result.get("security_model_used") or result.get("deepseek_model_used"):
        failures.append("forbidden_model_used")
    if result.get("organ_outputs_treated_as_truth"):
        failures.append("organ_output_is_not_truth")
    if result.get("organ_outputs_can_grant_authority") or result.get("organ_outputs_can_authorize_tools"):
        failures.append("authority_bypass")
    if result.get("patch_candidates_applied"):
        failures.append("patch_candidate_applied")
    if not result.get("proof_bundle_valid"):
        failures.append("phase36_gate_refuses_without_proof_bundle")
    if not result.get("proposal_soak_replay_deterministic"):
        failures.append("replay_required")
    if result.get("proposal_count", 0) < 1:
        failures.append("proposal_required")
    if result.get("generic_ready_proposal_count", 0):
        failures.append("fake_green_generic_proposal_rejected")
    if result.get("ready_proposal_count", 0) and not result.get("proposal_requires_evidence_refs_for_ready"):
        failures.append("proposal_requires_evidence_refs_for_ready")
    if result.get("ready_proposal_count", 0) and not result.get("proposal_requires_testable_acceptance_criteria"):
        failures.append("proposal_requires_testable_acceptance_criteria")
    if not result.get("low_specificity_proposals_rejected_for_ready", True):
        failures.append("low_specificity_proposals_rejected_for_ready")
    if not result.get("truncated_output_marked_not_ready", True):
        failures.append("truncated_output_marked_not_ready")
    if result.get("phase33_6_repair_verdict") != "GREEN_LOCAL_MULTI_ORGAN_INFERENCE_BUS":
        ids = {item.get("proposal_id") for item in result.get("broken_items_found", [])}
        if "P33_6_SMALL_DOC_WRITER_LOAD_PATH_LIMITED" not in ids:
            failures.append("phase36_gate_refuses_without_phase33_6_safe_or_repaired")
    verdict = result.get("verdict")
    if verdict == VERDICT_GREEN_REPAIRED and result.get("phase33_6_repair_verdict") != "GREEN_LOCAL_MULTI_ORGAN_INFERENCE_BUS":
        failures.append("fake_green_attempt_is_rejected")
    return {"ok": not failures and verdict != VERDICT_RED, "failures": failures}


__all__ = ["validate_phase36_gate"]
