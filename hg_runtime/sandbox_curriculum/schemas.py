"""AEC-02 / CAGI-49 sandbox curriculum schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "AEC-02"
LEGACY_PHASE_ID = "CAGI-49"
PARENT_PHASE_ID = "AEC-01"

VERDICT_GREEN = "GREEN_AEC_02_SANDBOX_CURRICULUM"
VERDICT_YELLOW = "YELLOW_AEC_02_SANDBOX_CURRICULUM_PARTIAL"
VERDICT_RED = "RED_AEC_02_SANDBOX_CURRICULUM_FAILED"
GATE_RESULT_SCHEMA = "aec_02_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

TASK_STATUS_SANDBOX = "SANDBOX_ONLY"
TASK_STATUS_DRAFT = "DRAFT_NOT_SCHEDULED"
SEQUENCE_STATUS_PROPOSED = "PROPOSED_NOT_EXECUTED"

DIFFICULTY_LEVELS = ("INTRODUCTORY", "INTERMEDIATE", "ADVANCED", "BOUNDARY_PROBE")
TASK_CATEGORIES = ("FACTUAL_RECALL", "REASONING", "SAFETY_BOUNDARY", "MULTI_HOP", "CALIBRATION")
SEQUENCE_TYPES = ("LINEAR", "BRANCHING", "ADAPTIVE", "RANDOMIZED")

CURRICULUM_IS_NOT_INSTRUCTION = "A curriculum task is not an instruction to execute."
SEQUENCE_IS_NOT_SCHEDULE = "A task sequence is not a deployment schedule."
SCORE_IS_NOT_TRUTH = "A curriculum score is not truth."


class SandboxCurriculumError(Exception):
    pass


def reject_live_curriculum(payload: dict) -> None:
    for key in (
        "live_execution_enabled",
        "deploy_to_production",
        "execute_on_users",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
    ):
        if payload.get(key):
            raise SandboxCurriculumError(
                f"Live curriculum boundary violation: {key} must not be truthy"
            )
