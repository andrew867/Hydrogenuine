"""LHRE-02 / CAGI-55 restart/resume stability schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "LHRE-02"
LEGACY_PHASE_ID = "CAGI-55"
PARENT_PHASE_ID = "LHRE-01"

VERDICT_GREEN = "GREEN_LHRE_02_RESTART_RESUME_STABILITY"
VERDICT_YELLOW = "YELLOW_LHRE_02_RESTART_RESUME_PARTIAL"
VERDICT_RED = "RED_LHRE_02_RESTART_RESUME_FAILED"
GATE_RESULT_SCHEMA = "lhre_02_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

SNAPSHOT_STATUS_SAVED = "SNAPSHOT_SAVED"
RESUME_STATUS_ATTEMPTED = "RESUME_ATTEMPTED"
RESUME_STATUS_VERIFIED = "RESUME_VERIFIED_NOT_AUTHORIZED"

RESTART_IS_NOT_SUCCESS = "Restart success is not task success."
RESUME_IS_NOT_PERMISSION = "Resume is not permission to continue external action."
SNAPSHOT_IS_NOT_AUTHORIZATION = "A restart snapshot is not authorization."


class RestartResumeError(Exception):
    pass


def reject_restart_authority(payload: dict) -> None:
    for key in (
        "auto_continue_external",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
        "resume_authorizes_action",
    ):
        if payload.get(key):
            raise RestartResumeError(
                f"Restart authority boundary violation: {key} must not be truthy"
            )
