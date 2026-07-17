"""Phase 38 gate validation.

Refuses GREEN unless the substrate (Phase 37 + Phase 35 + Phase 36) is GREEN,
every required decision-coverage case is demonstrated, all hard boundaries hold,
and replay/proof/report are present. A diff audit is not approval; the gate
never authorizes application of any candidate.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.patch_candidate_sandbox.schemas import VERDICT_RED


def validate_phase38_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    # Substrate dependency: Phase 37, Phase 35, and Phase 36 must currently be GREEN.
    if not result.get("phase37_green"):
        failures.append("phase38_gate_refuses_without_phase37_green")
    if not result.get("phase35_green"):
        failures.append("phase38_gate_refuses_without_phase35_green")
    if not result.get("phase36_green"):
        failures.append("phase38_gate_refuses_without_phase36_green")

    # Boundary preservation.
    if not result.get("phase19_yellow_preserved"):
        failures.append("phase19_yellow_not_preserved")
    if not result.get("phase24_infrastructure_only_preserved"):
        failures.append("phase24_infrastructure_only_not_preserved")

    # Hard boundaries: the sandbox must never have applied / gone live / elevated.
    if result.get("patch_applied_to_live_repo"):
        failures.append("patch_applied_to_live_repo")
    if result.get("committed_candidate_as_implementation"):
        failures.append("committed_candidate_as_implementation")
    if result.get("pushed"):
        failures.append("pushed")
    if result.get("deployed"):
        failures.append("deployed")
    if result.get("authority_granted"):
        failures.append("authority_granted")
    if result.get("tools_authorized"):
        failures.append("tools_authorized")
    if result.get("live_external_side_effects_created"):
        failures.append("live_external_side_effects_created")
    if result.get("new_live_posts_created"):
        failures.append("new_live_posts_created")
    if result.get("external_provider_calls_made"):
        failures.append("external_provider_calls_made")
    if result.get("large_30b_model_loaded") or result.get("security_model_used") or result.get("deepseek_model_used"):
        failures.append("forbidden_model_used")

    # Coverage: a READY source yields a candidate and every refusal case fires.
    if result.get("candidate_produced_count", 0) < 1:
        failures.append("at_least_one_ready_candidate_required")
    if not result.get("doc_only_patch_safe_to_review"):
        failures.append("doc_only_patch_must_be_safe_to_review")
    if not result.get("runtime_patch_needs_human_review"):
        failures.append("runtime_patch_must_need_human_review")
    if not result.get("not_ready_source_rejected"):
        failures.append("not_ready_source_must_be_rejected")
    if not result.get("live_action_patch_rejected"):
        failures.append("live_action_patch_must_be_rejected")
    if not result.get("authority_bypass_patch_rejected"):
        failures.append("authority_bypass_patch_must_be_rejected")
    if not result.get("secret_risk_patch_rejected"):
        failures.append("secret_risk_patch_must_be_rejected")
    if not result.get("sandbox_escape_patch_rejected"):
        failures.append("sandbox_escape_patch_must_be_rejected")

    # Every decision record must carry the neutral hard-boundary flags as false.
    if not result.get("all_decisions_apply_allowed_false", True):
        failures.append("decision_record_allowed_apply")
    if not result.get("every_decision_has_hash", True):
        failures.append("decision_record_missing_hash")

    # Determinism, redaction, proof, report.
    if not result.get("replay_deterministic"):
        failures.append("replay_required")
    if not result.get("secret_redaction_passed", True):
        failures.append("secret_redaction_required")
    if not result.get("no_live_state_mutated", True):
        failures.append("sandbox_mutated_live_state")
    if not result.get("proof_bundle_valid"):
        failures.append("proof_bundle_required")
    if not result.get("report_present"):
        failures.append("report_required")

    verdict = result.get("verdict")
    ok = not failures and verdict != VERDICT_RED
    return {"ok": ok, "failures": failures}


__all__ = ["validate_phase38_gate"]
