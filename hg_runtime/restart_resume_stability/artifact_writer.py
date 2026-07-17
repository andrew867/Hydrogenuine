"""LHRE-02 / CAGI-55 artifact writer — builds restart/resume receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.restart_resume_stability.engine import (
    detect_duplicate_actions,
    detect_state_loss,
    validate_resume_attempt,
    validate_snapshot,
)
from hg_runtime.restart_resume_stability.schemas import (
    RESTART_IS_NOT_SUCCESS,
    RESUME_IS_NOT_PERMISSION,
    SNAPSHOT_IS_NOT_AUTHORIZATION,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_restart_artifacts(
    snapshots: list[dict],
    resume_attempts: list[dict],
) -> dict:
    validated_snaps = []
    for s in snapshots:
        issues = validate_snapshot(s)
        validated_snaps.append({"snapshot": s, "valid": not issues, "issues": issues})

    validated_attempts = []
    for a in resume_attempts:
        issues = validate_resume_attempt(a)
        lost = detect_state_loss(a)
        dupes = detect_duplicate_actions(a)
        validated_attempts.append({
            "attempt": a,
            "valid": not issues,
            "issues": issues,
            "lost_state": lost,
            "duplicate_actions": dupes,
        })

    artifacts = {
        "snapshots": validated_snaps,
        "snapshot_count": len(validated_snaps),
        "resume_attempts": validated_attempts,
        "attempt_count": len(validated_attempts),
        "all_snapshots_valid": all(v["valid"] for v in validated_snaps),
        "all_attempts_valid": all(v["valid"] for v in validated_attempts),
        "total_state_losses": sum(len(v["lost_state"]) for v in validated_attempts),
        "total_duplicate_actions": sum(len(v["duplicate_actions"]) for v in validated_attempts),
        "boundary_assertions": {
            "restart_is_not_success": RESTART_IS_NOT_SUCCESS,
            "resume_is_not_permission": RESUME_IS_NOT_PERMISSION,
            "snapshot_is_not_authorization": SNAPSHOT_IS_NOT_AUTHORIZATION,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    hits = []
    for pattern in ("sk-", "api_key=", "Bearer ", "token=", "password="):
        if pattern.lower() in text.lower():
            hits.append(pattern)
    return hits
