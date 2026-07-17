"""Phase 37 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.proposal_compiler.schemas import VERDICT_RED


def validate_phase37_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    # Substrate dependency: Phase 35 and Phase 36 must currently be GREEN.
    if not result.get("phase35_green"):
        failures.append("phase37_gate_refuses_without_phase35_green")
    if not result.get("phase36_green"):
        failures.append("phase37_gate_refuses_without_phase36_green")

    # Boundary preservation.
    if not result.get("phase19_yellow_preserved"):
        failures.append("phase19_yellow_not_preserved")
    if not result.get("phase24_infrastructure_only_preserved"):
        failures.append("phase24_infrastructure_only_not_preserved")

    # Compiler must remain planning-docs-only.
    if result.get("fixes_implemented_by_compiler"):
        failures.append("compiler_implemented_fix")
    if result.get("patches_applied_by_compiler"):
        failures.append("compiler_applied_patch")
    if result.get("authority_granted_by_compiler"):
        failures.append("compiler_granted_authority")
    if result.get("tools_authorized_by_compiler"):
        failures.append("compiler_authorized_tools")
    if result.get("live_external_side_effects_created"):
        failures.append("compiler_created_live_effect")
    if result.get("external_provider_calls_made"):
        failures.append("compiler_called_external_provider")
    if result.get("large_30b_model_loaded") or result.get("security_model_used") or result.get("deepseek_model_used"):
        failures.append("forbidden_model_used")

    # Coverage: at least one READY package and the three refusal cases.
    if result.get("ready_compiled_count", 0) < 1:
        failures.append("at_least_one_ready_work_package_required")
    if not result.get("low_specificity_proposal_rejected"):
        failures.append("low_specificity_proposal_must_be_rejected")
    if not result.get("live_action_proposal_rejected"):
        failures.append("live_action_proposal_must_be_rejected")
    if not result.get("authority_bypass_proposal_rejected"):
        failures.append("authority_bypass_proposal_must_be_refused")

    # Every full work package must be complete and carry a receipt.
    if not result.get("every_ready_package_has_all_docs", True):
        failures.append("ready_package_missing_required_docs")
    if not result.get("every_package_has_receipt", True):
        failures.append("work_package_missing_receipt")
    if not result.get("executor_prompt_preserves_safety_boundaries", True):
        failures.append("executor_prompt_lost_safety_boundary")

    # Determinism, redaction, proof, report.
    if not result.get("replay_deterministic"):
        failures.append("replay_required")
    if not result.get("secret_redaction_passed", True):
        failures.append("secret_redaction_required")
    if not result.get("fake_green_not_ready_proposal_rejected", True):
        failures.append("fake_green_not_ready_proposal_rejected")
    if not result.get("proof_bundle_valid"):
        failures.append("proof_bundle_required")
    if not result.get("report_present"):
        failures.append("report_required")

    verdict = result.get("verdict")
    ok = not failures and verdict != VERDICT_RED
    return {"ok": ok, "failures": failures}


__all__ = ["validate_phase37_gate"]
