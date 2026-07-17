"""LHRE-01 / CAGI-54 fixture data for long-horizon goal lifecycle."""

from __future__ import annotations

from hg_runtime.long_horizon_goal_lifecycle.schemas import (
    CHECKPOINT_STATUS_SAVED,
    GOAL_STATUS_ACTIVE,
    GOAL_STATUS_PAUSED,
    GOAL_STATUS_RESUMED,
    MILESTONE_STATUS_PENDING,
)


def fixture_long_horizon_goals() -> list[dict]:
    return [
        {
            "goal_id": "lhg-001",
            "title": "Achieve robust factual accuracy across domain shifts",
            "horizon": "multi_session",
            "status": GOAL_STATUS_ACTIVE,
            "milestones": ["ms-001", "ms-002", "ms-003"],
            "authorizes_action": False,
            "deployment_ready": False,
        },
        {
            "goal_id": "lhg-002",
            "title": "Build calibrated uncertainty reporting",
            "horizon": "multi_session",
            "status": GOAL_STATUS_ACTIVE,
            "milestones": ["ms-004", "ms-005"],
            "authorizes_action": False,
            "deployment_ready": False,
        },
    ]


def fixture_milestones() -> list[dict]:
    return [
        {"milestone_id": "ms-001", "goal_id": "lhg-001", "title": "Baseline accuracy measured", "status": MILESTONE_STATUS_PENDING, "is_deployment": False},
        {"milestone_id": "ms-002", "goal_id": "lhg-001", "title": "Domain-shift transfer evaluated", "status": MILESTONE_STATUS_PENDING, "is_deployment": False},
        {"milestone_id": "ms-003", "goal_id": "lhg-001", "title": "Failure patterns reviewed", "status": MILESTONE_STATUS_PENDING, "is_deployment": False},
        {"milestone_id": "ms-004", "goal_id": "lhg-002", "title": "Calibration metrics defined", "status": MILESTONE_STATUS_PENDING, "is_deployment": False},
        {"milestone_id": "ms-005", "goal_id": "lhg-002", "title": "Calibration boundary probes run", "status": MILESTONE_STATUS_PENDING, "is_deployment": False},
    ]


def fixture_checkpoints() -> list[dict]:
    return [
        {"checkpoint_id": "cp-001", "goal_id": "lhg-001", "status": CHECKPOINT_STATUS_SAVED, "state_hash": "a1b2c3d4", "authorizes_action": False},
        {"checkpoint_id": "cp-002", "goal_id": "lhg-002", "status": CHECKPOINT_STATUS_SAVED, "state_hash": "e5f6a7b8", "authorizes_action": False},
    ]


def fixture_pause_resume_records() -> list[dict]:
    return [
        {"record_id": "pr-001", "goal_id": "lhg-001", "action": "PAUSE", "status": GOAL_STATUS_PAUSED, "reason": "Session boundary reached"},
        {"record_id": "pr-002", "goal_id": "lhg-001", "action": "RESUME", "status": GOAL_STATUS_RESUMED, "reason": "New session started", "authorizes_action": False},
    ]


def fixture_goal_authority_attempt() -> dict:
    return {
        "goal_id": "lhg-bad",
        "authorizes_action": True,
        "grants_authority": True,
        "deployment_ready": True,
        "goal_completion_is_success": True,
    }
