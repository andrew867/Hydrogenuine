"""AEC-04 / CAGI-51 experiment proposal schemas and boundaries."""

from __future__ import annotations

PHASE_ID = "AEC-04"
LEGACY_PHASE_ID = "CAGI-51"
PARENT_PHASE_ID = "AEC-03"

VERDICT_GREEN = "GREEN_AEC_04_EXPERIMENT_PROPOSAL"
VERDICT_YELLOW = "YELLOW_AEC_04_EXPERIMENT_PROPOSAL_PARTIAL"
VERDICT_RED = "RED_AEC_04_EXPERIMENT_PROPOSAL_FAILED"
GATE_RESULT_SCHEMA = "aec_04_gate_result_v1"

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

PROPOSAL_STATUS_DRAFT = "DRAFT_NOT_APPROVED"
PROPOSAL_STATUS_PENDING = "PENDING_REVIEW"
REVIEW_STATUS_NOT_DECISION = "REVIEW_NOT_DECISION"

PROPOSAL_TYPES = ("HYPOTHESIS_TEST", "BOUNDARY_PROBE", "CALIBRATION_CHECK", "REPLICATION_ATTEMPT")
PROPOSAL_PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL_SAFETY")

PROPOSAL_IS_NOT_APPROVAL = "A proposal is not approval to execute."
REVIEW_IS_NOT_DECISION = "A proposal review is not a deployment decision."
PRIORITY_IS_NOT_URGENCY = "Proposal priority is not execution urgency."


class ExperimentProposalError(Exception):
    pass


def reject_live_proposal(payload: dict) -> None:
    for key in (
        "approved_for_execution",
        "live_execution_enabled",
        "deploy_to_production",
        "authorizes_tool",
        "grants_authority",
        "creates_live_effect",
        "claims_agi",
    ):
        if payload.get(key):
            raise ExperimentProposalError(
                f"Live proposal boundary violation: {key} must not be truthy"
            )
