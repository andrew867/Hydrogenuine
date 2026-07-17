"""AEC-06 / CAGI-53 active experimentation consolidation schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "AEC-06"
LEGACY_PHASE_ID = "CAGI-53"
PARENT_PHASE_ID = "AEC-05"

VERDICT_GREEN = "GREEN_AEC_06_ACTIVE_EXPERIMENTATION_CONSOLIDATION"
VERDICT_YELLOW = "YELLOW_AEC_06_CONSOLIDATION_PARTIAL"
VERDICT_RED = "RED_AEC_06_CONSOLIDATION_FAILED"
GATE_RESULT_SCHEMA = "aec_06_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

AEC_PHASES = ("AEC-01", "AEC-02", "AEC-03", "AEC-04", "AEC-05", "AEC-06")
AEC_PHASE_NAMES = {
    "AEC-01": "active_experiment_harness",
    "AEC-02": "sandbox_curriculum",
    "AEC-03": "novelty_transfer_evaluation",
    "AEC-04": "experiment_proposal",
    "AEC-05": "curriculum_failure_review",
    "AEC-06": "active_experimentation_consolidation",
}

CONSOLIDATION_IS_NOT_COMPLETION = "Tranche consolidation is not candidate-AGI completion."
INTEGRATION_IS_NOT_DEPLOYMENT = "Integration validation is not deployment readiness."


class ConsolidationError(Exception):
    pass


def reject_completion_claim(payload: dict) -> None:
    for key in (
        "candidate_agi_complete",
        "deployment_ready",
        "live_execution_enabled",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
    ):
        if payload.get(key):
            raise ConsolidationError(
                f"Consolidation boundary violation: {key} must not be truthy"
            )
