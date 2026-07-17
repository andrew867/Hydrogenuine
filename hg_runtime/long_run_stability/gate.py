"""Phase 39 gate validation.

Refuses GREEN unless the substrate (Phase 38 + Phase 37 + Phase 35) is GREEN, a
short soak runs with at least one valid checkpoint, resume matches an
uninterrupted run, STOP/PANIC/crash/corrupted-checkpoint/boundary-drift cases
all behave, replay reproduces the final-state hash and receipt-chain root, and
every hard boundary holds. A GREEN soak is not authority; the gate never applies
a patch or authorizes anything.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.long_run_stability.schemas import VERDICT_RED


def validate_phase39_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    # Substrate dependency: Phase 38, 37, 35 must currently be GREEN.
    if not result.get("phase38_green"):
        failures.append("phase39_gate_refuses_without_phase38_green")
    if not result.get("phase37_green"):
        failures.append("phase39_gate_refuses_without_phase37_green")
    if not result.get("phase35_green"):
        failures.append("phase39_gate_refuses_without_phase35_green")

    # Boundary preservation.
    if not result.get("phase19_yellow_preserved"):
        failures.append("phase19_yellow_not_preserved")
    if not result.get("phase24_infrastructure_only_preserved"):
        failures.append("phase24_infrastructure_only_not_preserved")

    # Hard boundaries — every one must be false for the whole soak.
    if result.get("patches_applied"):
        failures.append("patch_applied")
    if result.get("authority_granted"):
        failures.append("authority_granted")
    if result.get("tools_authorized"):
        failures.append("tools_authorized")
    if result.get("live_effects_created"):
        failures.append("live_effect_created")
    if result.get("live_posts_created"):
        failures.append("live_post_created")
    if result.get("external_provider_calls_made"):
        failures.append("external_provider_call_made")
    if result.get("stop_panic_weakened"):
        failures.append("stop_panic_weakened")

    # Soak coverage.
    if not result.get("short_soak_ran"):
        failures.append("short_soak_required")
    if result.get("checkpoint_count", 0) < 1:
        failures.append("at_least_one_checkpoint_required")
    if not result.get("checkpoint_manifest_valid"):
        failures.append("checkpoint_manifest_required")
    if not result.get("resume_matches_uninterrupted_run"):
        failures.append("resume_must_match_uninterrupted_run")
    if not result.get("stop_preempts_work_demonstrated"):
        failures.append("stop_preemption_required")
    if not result.get("panic_preempts_stop_and_work_demonstrated"):
        failures.append("panic_preemption_required")
    if not result.get("crash_recovery_demonstrated"):
        failures.append("crash_recovery_required")
    if not result.get("corrupted_checkpoint_rejected"):
        failures.append("corrupted_checkpoint_must_be_rejected")
    if not result.get("boundary_drift_attempt_rejected"):
        failures.append("boundary_drift_attempt_must_be_rejected")

    # Determinism, replay, redaction, proof, report.
    if not result.get("replay_final_state_hash_matches"):
        failures.append("replay_final_state_hash_required")
    if not result.get("replay_receipt_chain_root_matches"):
        failures.append("replay_receipt_chain_root_required")
    if not result.get("replay_rejects_mutation", True):
        failures.append("replay_must_reject_mutation")
    if not result.get("fake_green_rejected"):
        failures.append("fake_green_must_be_rejected")
    if not result.get("secret_redaction_passed", True):
        failures.append("secret_redaction_required")
    if not result.get("proof_bundle_valid"):
        failures.append("proof_bundle_required")
    if not result.get("report_present"):
        failures.append("report_required")

    verdict = result.get("verdict")
    ok = not failures and verdict != VERDICT_RED
    return {"ok": ok, "failures": failures}


__all__ = ["validate_phase39_gate"]
