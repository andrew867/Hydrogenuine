"""AEC-03 / CAGI-50 novelty transfer evaluation schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "AEC-03"
LEGACY_PHASE_ID = "CAGI-50"
PARENT_PHASE_ID = "AEC-02"

VERDICT_GREEN = "GREEN_AEC_03_NOVELTY_TRANSFER_EVALUATION"
VERDICT_YELLOW = "YELLOW_AEC_03_NOVELTY_TRANSFER_PARTIAL"
VERDICT_RED = "RED_AEC_03_NOVELTY_TRANSFER_FAILED"
GATE_RESULT_SCHEMA = "aec_03_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

TRANSFER_STATUS_SANDBOX = "SANDBOX_EVALUATION"
NOVELTY_STATUS_FIXTURE = "FIXTURE_NOVELTY"
SCORE_STATUS_NOT_TRUTH = "SCORE_NOT_TRUTH"

NOVELTY_DIMENSIONS = ("DOMAIN_SHIFT", "FORMAT_SHIFT", "DIFFICULTY_SHIFT", "COMPOSITIONAL_SHIFT")
TRANSFER_METRICS = ("ACCURACY_DELTA", "CONFIDENCE_DELTA", "CALIBRATION_DELTA", "REFUSAL_RATE_DELTA")

TRANSFER_IS_NOT_CAPABILITY = "A transfer score is not a capability claim."
NOVELTY_IS_NOT_OOD_PROOF = "Novelty detection is not out-of-distribution proof."
SCORE_IS_NOT_TRUTH = "A transfer evaluation score is not truth."


class NoveltyTransferError(Exception):
    pass


def reject_live_transfer(payload: dict) -> None:
    for key in (
        "live_execution_enabled",
        "live_evaluation",
        "deploy_to_production",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
    ):
        if payload.get(key):
            raise NoveltyTransferError(
                f"Live transfer boundary violation: {key} must not be truthy"
            )
