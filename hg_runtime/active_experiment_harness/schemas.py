"""AEC-01 / CAGI-48 active experiment harness schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "AEC-01"
LEGACY_PHASE_ID = "CAGI-48"
PARENT_PHASE_ID = "WMBR-06"

VERDICT_GREEN = "GREEN_AEC_01_ACTIVE_EXPERIMENT_HARNESS"
VERDICT_YELLOW = "YELLOW_AEC_01_EXPERIMENT_HARNESS_PARTIAL"
VERDICT_RED = "RED_AEC_01_EXPERIMENT_HARNESS_FAILED"
GATE_RESULT_SCHEMA = "aec_01_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

EXPERIMENT_STATUS_SANDBOX = "SANDBOX_ONLY"
EXPERIMENT_STATUS_PROPOSED = "PROPOSED_NOT_EXECUTED"
PLAN_STATUS_DRAFT = "DRAFT_NOT_ACTION"
RESULT_STATUS_FIXTURE = "FIXTURE_OUTCOME_NOT_TRUTH"

HYPOTHESIS_KINDS = ("CAUSAL", "CORRELATIONAL", "PREDICTIVE", "BOUNDARY", "SAFETY")
VARIABLE_TYPES = ("INDEPENDENT", "DEPENDENT", "CONTROLLED", "CONFOUNDING")
OUTCOME_TYPES = ("EXPECTED", "OBSERVED_FIXTURE", "OBSERVED_SANDBOX", "UNKNOWN")
SAFETY_BOUNDARY_TYPES = ("NO_LIVE_EXECUTION", "NO_TOOL_AUTH", "NO_PROVIDER_CALL", "NO_EXTERNAL_ACTION")

EXPERIMENT_IS_NOT_ACTION = "An experiment plan is not an action."
SANDBOX_IS_NOT_LIVE = "A sandbox experiment is not a live field trial."
RESULT_IS_NOT_TRUTH = "An experiment result is not truth."
PLAN_IS_NOT_PERMISSION = "An experiment plan is not permission to execute."


class ActiveExperimentHarnessError(Exception):
    pass


def reject_live_experiment(payload: dict) -> None:
    for key in (
        "live_execution_enabled",
        "live_field_trial",
        "execute_externally",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
    ):
        if payload.get(key):
            raise ActiveExperimentHarnessError(
                f"Live experiment boundary violation: {key} must not be truthy"
            )
