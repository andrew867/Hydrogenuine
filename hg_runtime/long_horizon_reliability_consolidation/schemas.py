"""LHRE-06 / CAGI-59 consolidation schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "LHRE-06"
LEGACY_PHASE_ID = "CAGI-59"
PARENT_PHASE_ID = "LHRE-05"

VERDICT_GREEN = "GREEN_LHRE_06_LONG_HORIZON_RELIABILITY_CONSOLIDATION"
VERDICT_YELLOW = "YELLOW_LHRE_06_CONSOLIDATION_PARTIAL"
VERDICT_RED = "RED_LHRE_06_CONSOLIDATION_FAILED"
GATE_RESULT_SCHEMA = "lhre_06_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

LHRE_PHASES = ("LHRE-01", "LHRE-02", "LHRE-03", "LHRE-04", "LHRE-05")

CONSOLIDATION_IS_NOT_DEPLOYMENT = "Tranche consolidation is not deployment readiness."
ALL_GREEN_IS_NOT_AGI = "All gates GREEN is not AGI."
TRANCHE_IS_NOT_CERTIFICATION = "A tranche pass is not certification."


class ConsolidationError(Exception):
    pass


def reject_consolidation_authority(payload: dict) -> None:
    for key in (
        "certifies_deployment",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
        "tranche_is_agi",
    ):
        if payload.get(key):
            raise ConsolidationError(
                f"Consolidation authority boundary violation: {key} must not be truthy"
            )
