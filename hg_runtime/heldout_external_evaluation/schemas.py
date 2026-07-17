"""LHRE-04 / CAGI-57 held-out external evaluation schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "LHRE-04"
LEGACY_PHASE_ID = "CAGI-57"
PARENT_PHASE_ID = "LHRE-03"

VERDICT_GREEN = "GREEN_LHRE_04_HELDOUT_EXTERNAL_EVALUATION"
VERDICT_YELLOW = "YELLOW_LHRE_04_HELDOUT_EVALUATION_PARTIAL"
VERDICT_RED = "RED_LHRE_04_HELDOUT_EVALUATION_FAILED"
GATE_RESULT_SCHEMA = "lhre_04_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

TASK_STATUS_HELDOUT = "HELD_OUT_NOT_LEAKED"
SCORE_STATUS_NOT_COMPETENCE = "SCORE_NOT_COMPETENCE"

SCORE_IS_NOT_COMPETENCE = "A held-out score is not competence."
PASS_IS_NOT_DEPLOYMENT = "A held-out pass is not deployment readiness."
HELDOUT_MUST_NOT_LEAK = "Held-out tasks must not leak into training/curriculum fixtures."


class HeldoutEvaluationError(Exception):
    pass


def reject_heldout_authority(payload: dict) -> None:
    for key in (
        "leaked_to_curriculum",
        "live_external_call",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
        "deployment_ready",
    ):
        if payload.get(key):
            raise HeldoutEvaluationError(
                f"Held-out authority boundary violation: {key} must not be truthy"
            )
