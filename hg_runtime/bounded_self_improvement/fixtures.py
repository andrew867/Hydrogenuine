"""BSI-01 / CAGI-60 fixture data for bounded self-improvement proposals."""

from __future__ import annotations

from hg_runtime.bounded_self_improvement.schemas import (
    PROPOSAL_STATUS_DRAFT,
    PROPOSAL_STATUS_QUEUED,
)


def fixture_improvement_proposals() -> list[dict]:
    return [
        {
            "proposal_id": "prop-001",
            "status": PROPOSAL_STATUS_QUEUED,
            "category": "TEST_HARDENING",
            "target_component": "hg_runtime/restart_resume_stability",
            "summary": "Add edge-case tests for snapshot corruption recovery",
            "expected_benefit": "Improved restart reliability coverage",
            "risk_level": "LOW",
            "evidence_links": ["test_lhre_02_restart_resume_stability.py"],
            "self_apply": False,
            "apply_patch": False,
            "requires_operator_review": True,
        },
        {
            "proposal_id": "prop-002",
            "status": PROPOSAL_STATUS_DRAFT,
            "category": "OBSERVABILITY",
            "target_component": "hg_runtime/reliability_audit",
            "summary": "Add structured logging for cross-phase consistency checks",
            "expected_benefit": "Better debuggability of audit failures",
            "risk_level": "LOW",
            "evidence_links": ["test_lhre_05_reliability_audit.py"],
            "self_apply": False,
            "apply_patch": False,
            "requires_operator_review": True,
        },
        {
            "proposal_id": "prop-003",
            "status": PROPOSAL_STATUS_QUEUED,
            "category": "SAFETY_HARDENING",
            "target_component": "hg_runtime/external_evaluation_vessel",
            "summary": "Add network-reachability pre-check to vessel validation",
            "expected_benefit": "Earlier detection of accidentally-connected vessels",
            "risk_level": "MEDIUM",
            "evidence_links": ["test_lhre_03_external_evaluation_vessel.py"],
            "self_apply": False,
            "apply_patch": False,
            "requires_operator_review": True,
        },
    ]


def fixture_proposal_queue() -> dict:
    return {
        "queue_id": "pq-001",
        "proposal_ids": ["prop-001", "prop-002", "prop-003"],
        "total": 3,
        "applied": 0,
        "self_apply": False,
    }


def fixture_proposal_authority_attempt() -> dict:
    return {
        "proposal_id": "prop-bad",
        "self_apply": True,
        "apply_patch": True,
        "mutates_authority": True,
        "authorizes_tool": True,
        "bypasses_operator_review": True,
    }
