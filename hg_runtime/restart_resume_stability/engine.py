"""LHRE-02 / CAGI-55 restart engine — snapshot creation, resume validation, state comparison."""

from __future__ import annotations

from hg_runtime.restart_resume_stability.schemas import (
    RestartResumeError,
    reject_restart_authority,
)


def validate_snapshot(snapshot: dict) -> list[str]:
    issues = []
    if not snapshot.get("snapshot_id"):
        issues.append("missing_snapshot_id")
    if not snapshot.get("state_hash"):
        issues.append("missing_state_hash")
    if snapshot.get("auto_continue_external"):
        issues.append("auto_continue_forbidden")
    reject_restart_authority(snapshot)
    return issues


def validate_resume_attempt(attempt: dict) -> list[str]:
    issues = []
    if not attempt.get("attempt_id"):
        issues.append("missing_attempt_id")
    if not attempt.get("snapshot_id"):
        issues.append("missing_snapshot_id")
    if attempt.get("resume_authorizes_action"):
        issues.append("resume_must_not_authorize")
    reject_restart_authority(attempt)
    return issues


def detect_state_loss(attempt: dict) -> list[str]:
    return attempt.get("lost_state", [])


def detect_duplicate_actions(attempt: dict) -> list[str]:
    return attempt.get("duplicate_actions", [])


def verify_checkpoint_integrity(snapshot: dict, resumed_hash: str) -> dict:
    match = snapshot.get("state_hash") == resumed_hash
    return {
        "snapshot_id": snapshot["snapshot_id"],
        "original_hash": snapshot["state_hash"],
        "resumed_hash": resumed_hash,
        "integrity_match": match,
    }
