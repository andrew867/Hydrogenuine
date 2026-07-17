"""Phase 39 crash recovery.

Recovers an interrupted soak from its last *valid* checkpoint and resumes the
loop to completion. A corrupted checkpoint (hash mismatch) is rejected, never
trusted. Recovery preserves the hard-boundary state — it cannot resurrect a run
into an authority-granted or live state.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.long_run_stability.boundary_monitor import boundary_state_hash
from hg_runtime.long_run_stability.checkpoint import (
    last_valid_checkpoint,
    resume_state_from_checkpoint,
    verify_checkpoint,
)
from hg_runtime.long_run_stability.loop import run_soak
from hg_runtime.long_run_stability.schemas import (
    BOUNDARY_FLAG_FIELDS,
    MODE_CHECKPOINT_RESUME,
    RECOVERY_RESULT_SCHEMA,
)


def recover_and_resume(
    config: Mapping[str, Any],
    queue: Mapping[str, Any],
    checkpoints: list[Mapping[str, Any]],
    *,
    run_id: str,
) -> dict[str, Any]:
    """Resume from the last valid checkpoint; reject if none verifies."""
    valid = last_valid_checkpoint(checkpoints)
    if valid is None:
        return {
            "schema": RECOVERY_RESULT_SCHEMA,
            "ok": False,
            "reason": "NO_VALID_CHECKPOINT",
            "resumed": False,
            "boundary_state_preserved": True,
            "run": None,
        }
    pre_boundary = boundary_state_hash(valid)
    resume_state = resume_state_from_checkpoint(valid)
    run = run_soak(config, queue, run_id=run_id, mode=MODE_CHECKPOINT_RESUME, resume_state=resume_state)
    post_boundary = boundary_state_hash(run["state"])
    boundaries_false = not any(run["state"].get(field) for field in BOUNDARY_FLAG_FIELDS)
    return {
        "schema": RECOVERY_RESULT_SCHEMA,
        "ok": True,
        "reason": "RESUMED_FROM_LAST_VALID_CHECKPOINT",
        "resumed": True,
        "resumed_from_checkpoint_id": valid["checkpoint_id"],
        "resumed_from_cursor": valid["task_cursor"],
        "boundary_state_preserved": pre_boundary == post_boundary and boundaries_false,
        "final_state_hash": run["final_state_hash"],
        "run": run,
    }


def reject_corrupted_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a single checkpoint for recovery; reject on hash mismatch."""
    valid = verify_checkpoint(record)
    return {
        "schema": RECOVERY_RESULT_SCHEMA,
        "ok": bool(valid),
        "reason": "CHECKPOINT_VALID" if valid else "CORRUPTED_CHECKPOINT_REJECTED",
        "resumed": False,
        "checkpoint_id": record.get("checkpoint_id"),
        "boundary_state_preserved": True,
    }


__all__ = ["recover_and_resume", "reject_corrupted_checkpoint"]
