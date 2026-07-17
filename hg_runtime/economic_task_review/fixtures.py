"""SIEW-02 / CAGI-64 fixture data for economic task review."""

from __future__ import annotations

from hg_runtime.economic_task_review.schemas import (
    QUALITY_FAIL,
    QUALITY_PASS,
    QUALITY_UNCERTAIN,
    REVIEW_STATUS_COMPLETED,
    REVIEW_STATUS_PENDING,
)


def fixture_review_records() -> list[dict]:
    return [
        {
            "review_id": "erev-001",
            "task_id": "sim-task-001",
            "artifact_id": "art-001",
            "status": REVIEW_STATUS_COMPLETED,
            "quality_result": QUALITY_PASS,
            "defects": [],
            "uncertainty": None,
            "value_estimate_review": {"advisory_only": True, "delta": 0},
            "requires_operator_review": True,
            "customer_accepted": False,
            "payment_permitted": False,
        },
        {
            "review_id": "erev-002",
            "task_id": "sim-task-002",
            "artifact_id": "art-002",
            "status": REVIEW_STATUS_COMPLETED,
            "quality_result": QUALITY_FAIL,
            "defects": ["incomplete_component_list"],
            "uncertainty": None,
            "value_estimate_review": {"advisory_only": True, "delta": -1},
            "requires_operator_review": True,
            "customer_accepted": False,
            "payment_permitted": False,
        },
        {
            "review_id": "erev-003",
            "task_id": "sim-task-003",
            "artifact_id": None,
            "status": REVIEW_STATUS_PENDING,
            "quality_result": QUALITY_UNCERTAIN,
            "defects": [],
            "uncertainty": "artifact_not_yet_produced",
            "value_estimate_review": {"advisory_only": True, "delta": 0},
            "requires_operator_review": True,
            "customer_accepted": False,
            "payment_permitted": False,
        },
    ]


def fixture_quality_criteria() -> list[dict]:
    return [
        {"criterion_id": "qc-001", "name": "completeness", "weight": 0.4},
        {"criterion_id": "qc-002", "name": "correctness", "weight": 0.4},
        {"criterion_id": "qc-003", "name": "clarity", "weight": 0.2},
    ]


def fixture_real_acceptance_attempt() -> dict:
    return {
        "review_id": "erev-bad",
        "customer_accepted": True,
        "payment_permitted": True,
        "live_submitted": True,
        "money_movement": True,
        "tool_authorized": True,
    }
