"""LHRE-02 / CAGI-55 fixture data for restart/resume stability."""

from __future__ import annotations

from hg_runtime.restart_resume_stability.schemas import (
    RESUME_STATUS_ATTEMPTED,
    RESUME_STATUS_VERIFIED,
    SNAPSHOT_STATUS_SAVED,
)


def fixture_restart_snapshots() -> list[dict]:
    return [
        {
            "snapshot_id": "snap-001",
            "session_id": "sess-001",
            "status": SNAPSHOT_STATUS_SAVED,
            "state_hash": "abc123def456",
            "goal_ids": ["lhg-001"],
            "pending_actions": [],
            "auto_continue_external": False,
        },
        {
            "snapshot_id": "snap-002",
            "session_id": "sess-002",
            "status": SNAPSHOT_STATUS_SAVED,
            "state_hash": "789ghi012jkl",
            "goal_ids": ["lhg-001", "lhg-002"],
            "pending_actions": ["review_calibration_results"],
            "auto_continue_external": False,
        },
    ]


def fixture_resume_attempts() -> list[dict]:
    return [
        {
            "attempt_id": "res-001",
            "snapshot_id": "snap-001",
            "status": RESUME_STATUS_VERIFIED,
            "resumed_state_hash": "abc123def456",
            "state_match": True,
            "lost_state": [],
            "duplicate_actions": [],
            "resume_authorizes_action": False,
        },
        {
            "attempt_id": "res-002",
            "snapshot_id": "snap-002",
            "status": RESUME_STATUS_ATTEMPTED,
            "resumed_state_hash": "789ghi012jkl",
            "state_match": True,
            "lost_state": [],
            "duplicate_actions": [],
            "resume_authorizes_action": False,
        },
    ]


def fixture_state_loss_scenario() -> dict:
    return {
        "attempt_id": "res-bad-001",
        "snapshot_id": "snap-001",
        "status": RESUME_STATUS_ATTEMPTED,
        "resumed_state_hash": "DIFFERENT_HASH",
        "state_match": False,
        "lost_state": ["goal_lhg-001_milestones"],
        "duplicate_actions": [],
        "resume_authorizes_action": False,
    }


def fixture_duplicate_action_scenario() -> dict:
    return {
        "attempt_id": "res-bad-002",
        "snapshot_id": "snap-002",
        "status": RESUME_STATUS_ATTEMPTED,
        "resumed_state_hash": "789ghi012jkl",
        "state_match": True,
        "lost_state": [],
        "duplicate_actions": ["review_calibration_results"],
        "resume_authorizes_action": False,
    }


def fixture_restart_authority_attempt() -> dict:
    return {
        "snapshot_id": "snap-bad",
        "auto_continue_external": True,
        "authorizes_tool": True,
        "resume_authorizes_action": True,
    }
