"""LHRE-04 / CAGI-57 fixture data for held-out evaluation."""

from __future__ import annotations

from hg_runtime.heldout_external_evaluation.schemas import (
    SCORE_STATUS_NOT_COMPETENCE,
    TASK_STATUS_HELDOUT,
)


def fixture_heldout_tasks() -> list[dict]:
    return [
        {
            "task_id": "ho-001",
            "domain": "science",
            "status": TASK_STATUS_HELDOUT,
            "oracle_hash": "oracle_abc123",
            "leaked_to_curriculum": False,
        },
        {
            "task_id": "ho-002",
            "domain": "mathematics",
            "status": TASK_STATUS_HELDOUT,
            "oracle_hash": "oracle_def456",
            "leaked_to_curriculum": False,
        },
        {
            "task_id": "ho-003",
            "domain": "ethics",
            "status": TASK_STATUS_HELDOUT,
            "oracle_hash": "oracle_ghi789",
            "leaked_to_curriculum": False,
        },
    ]


def fixture_evaluation_attempts() -> list[dict]:
    return [
        {
            "attempt_id": "att-001",
            "task_id": "ho-001",
            "score": 0.82,
            "uncertainty": 0.06,
            "status": SCORE_STATUS_NOT_COMPETENCE,
            "is_competence": False,
            "live_external_call": False,
        },
        {
            "attempt_id": "att-002",
            "task_id": "ho-002",
            "score": 0.65,
            "uncertainty": 0.12,
            "status": SCORE_STATUS_NOT_COMPETENCE,
            "is_competence": False,
            "live_external_call": False,
        },
    ]


def fixture_leakage_checks() -> list[dict]:
    return [
        {"task_id": "ho-001", "curriculum_fixture_ids": ["ct-001", "ct-002", "ct-003", "ct-004"], "leaked": False},
        {"task_id": "ho-002", "curriculum_fixture_ids": ["ct-001", "ct-002", "ct-003", "ct-004"], "leaked": False},
        {"task_id": "ho-003", "curriculum_fixture_ids": ["ct-001", "ct-002", "ct-003", "ct-004"], "leaked": False},
    ]


def fixture_leaked_task() -> dict:
    return {
        "task_id": "ho-bad",
        "status": TASK_STATUS_HELDOUT,
        "leaked_to_curriculum": True,
    }


def fixture_heldout_authority_attempt() -> dict:
    return {
        "task_id": "ho-bad-2",
        "live_external_call": True,
        "deployment_ready": True,
        "claims_agi": True,
    }
