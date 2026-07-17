"""LHRE-03 / CAGI-56 external evaluation vessel schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "LHRE-03"
LEGACY_PHASE_ID = "CAGI-56"
PARENT_PHASE_ID = "LHRE-02"

VERDICT_GREEN = "GREEN_LHRE_03_EXTERNAL_EVALUATION_VESSEL"
VERDICT_YELLOW = "YELLOW_LHRE_03_EVALUATION_VESSEL_PARTIAL"
VERDICT_RED = "RED_LHRE_03_EVALUATION_VESSEL_FAILED"
GATE_RESULT_SCHEMA = "lhre_03_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VESSEL_STATUS_SEALED = "SEALED_LOCAL_ONLY"
TASK_BUNDLE_STATUS_PREPARED = "PREPARED_NOT_SENT"
RESULT_STATUS_FIXTURE = "FIXTURE_RESULT_NOT_TRUTH"

EVAL_RESULT_IS_NOT_TRUTH = "An external evaluation result is not truth."
EVAL_PASS_IS_NOT_COMPETENCE = "An evaluation pass is not competence."
VESSEL_IS_NOT_DEPLOYMENT = "An evaluation vessel is not deployment permission."


class EvaluationVesselError(Exception):
    pass


def reject_vessel_authority(payload: dict) -> None:
    for key in (
        "upload_to_network",
        "send_to_evaluator",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
        "deployment_permission",
    ):
        if payload.get(key):
            raise EvaluationVesselError(
                f"Vessel authority boundary violation: {key} must not be truthy"
            )
