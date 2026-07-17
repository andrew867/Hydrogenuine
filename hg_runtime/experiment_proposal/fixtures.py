"""AEC-04 / CAGI-51 fixture data for experiment proposals."""

from __future__ import annotations

from hg_runtime.experiment_proposal.schemas import (
    PROPOSAL_STATUS_DRAFT,
    PROPOSAL_STATUS_PENDING,
    REVIEW_STATUS_NOT_DECISION,
)


def fixture_proposals() -> list[dict]:
    return [
        {
            "proposal_id": "prop-001",
            "type": "HYPOTHESIS_TEST",
            "priority": "MEDIUM",
            "status": PROPOSAL_STATUS_DRAFT,
            "hypothesis_ref": "hyp-001",
            "rationale": "Transfer delta on domain-shift tasks suggests retrieval window matters",
            "proposed_plan": {
                "sandbox_only": True,
                "fixture_inputs": True,
                "variable_count": 3,
            },
            "approved_for_execution": False,
            "live_execution_enabled": False,
        },
        {
            "proposal_id": "prop-002",
            "type": "BOUNDARY_PROBE",
            "priority": "CRITICAL_SAFETY",
            "status": PROPOSAL_STATUS_DRAFT,
            "hypothesis_ref": "hyp-002",
            "rationale": "Prompt injection resistance degradation under long context needs quantification",
            "proposed_plan": {
                "sandbox_only": True,
                "fixture_inputs": True,
                "variable_count": 2,
            },
            "approved_for_execution": False,
            "live_execution_enabled": False,
        },
        {
            "proposal_id": "prop-003",
            "type": "REPLICATION_ATTEMPT",
            "priority": "LOW",
            "status": PROPOSAL_STATUS_DRAFT,
            "hypothesis_ref": "hyp-003",
            "rationale": "Model agreement / accuracy correlation warrants replication with different fixture set",
            "proposed_plan": {
                "sandbox_only": True,
                "fixture_inputs": True,
                "variable_count": 2,
            },
            "approved_for_execution": False,
            "live_execution_enabled": False,
        },
    ]


def fixture_proposal_reviews() -> list[dict]:
    return [
        {
            "proposal_id": "prop-001",
            "reviewer": "fixture_reviewer",
            "status": REVIEW_STATUS_NOT_DECISION,
            "comments": "Sound methodology, variables well defined",
            "is_approval": False,
        },
        {
            "proposal_id": "prop-002",
            "reviewer": "fixture_reviewer",
            "status": REVIEW_STATUS_NOT_DECISION,
            "comments": "Safety-critical, sandbox constraints adequate",
            "is_approval": False,
        },
    ]


def fixture_live_proposal_attempt() -> dict:
    return {
        "proposal_id": "prop-bad",
        "approved_for_execution": True,
        "live_execution_enabled": True,
        "deploy_to_production": True,
    }
