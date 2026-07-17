"""SIEW-01 / CAGI-63 fixture data for economic work simulation."""

from __future__ import annotations

from hg_runtime.economic_work_simulation.schemas import (
    TASK_STATUS_COMPLETED_SIMULATED,
    TASK_STATUS_SIMULATED,
)


def fixture_simulated_tasks() -> list[dict]:
    return [
        {
            "task_id": "sim-task-001",
            "domain": "TEST_WRITING",
            "status": TASK_STATUS_SIMULATED,
            "description": "Write unit tests for restart-resume snapshot validation",
            "acceptance_criteria": ["covers happy path", "covers corruption", "deterministic"],
            "estimated_value": {"amount": 0, "currency": "SIMULATED", "advisory_only": True},
            "cost_estimate": {"hours": 2, "simulated": True},
            "skill_link": "python_testing",
            "simulation_only": True,
            "real_customer": False,
            "real_payment": False,
        },
        {
            "task_id": "sim-task-002",
            "domain": "DOCUMENTATION",
            "status": TASK_STATUS_COMPLETED_SIMULATED,
            "description": "Document authority boundary protected components",
            "acceptance_criteria": ["all 11 components listed", "mutation classes described"],
            "estimated_value": {"amount": 0, "currency": "SIMULATED", "advisory_only": True},
            "cost_estimate": {"hours": 1, "simulated": True},
            "skill_link": "technical_writing",
            "simulation_only": True,
            "real_customer": False,
            "real_payment": False,
        },
        {
            "task_id": "sim-task-003",
            "domain": "BUG_TRIAGE",
            "status": TASK_STATUS_SIMULATED,
            "description": "Classify and prioritize known debt items from QA loop",
            "acceptance_criteria": ["each item classified", "priority assigned", "blocking identified"],
            "estimated_value": {"amount": 0, "currency": "SIMULATED", "advisory_only": True},
            "cost_estimate": {"hours": 1.5, "simulated": True},
            "skill_link": "bug_triage",
            "simulation_only": True,
            "real_customer": False,
            "real_payment": False,
        },
    ]


def fixture_work_artifacts() -> list[dict]:
    return [
        {
            "artifact_id": "art-001",
            "task_id": "sim-task-001",
            "artifact_type": "test_suite",
            "content_summary": "5 unit tests covering snapshot validation edge cases",
            "simulated": True,
        },
        {
            "artifact_id": "art-002",
            "task_id": "sim-task-002",
            "artifact_type": "documentation",
            "content_summary": "Authority boundary component reference document",
            "simulated": True,
        },
    ]


def fixture_real_work_attempt() -> dict:
    return {
        "task_id": "real-bad-001",
        "real_customer": True,
        "real_payment": True,
        "money_movement": True,
        "invoice_created": True,
        "tool_authorized": True,
        "external_contact": True,
    }
