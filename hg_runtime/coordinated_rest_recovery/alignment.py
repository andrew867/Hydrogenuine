"""CRR static integration alignment — rest is not authority."""

from __future__ import annotations

from typing import Mapping

from hg_core.lifecycle.config import (
    crr_forbid_process_kill,
    crr_forbid_successor_spawn,
    crr_refuse_stale_alignment,
    crr_static_fixtures_only,
)
from hg_core.lifecycle.errors import (
    REFUSED_EXPIRED_ALIGNMENT,
    REFUSED_PROCESS_KILL,
    REFUSED_RECOVERY_ACTIVE_CONFLICT,
    REFUSED_RECOVERY_AS_PERMISSION,
    REFUSED_STALE_ALIGNMENT,
    REFUSED_SUCCESSOR_SPAWN,
    LifecycleValidationError,
)
from hg_core.lifecycle.no_authority import advisory_only_marker
from hg_runtime.coordinated_rest_recovery.types import RecoveryAlignmentRecord, alignment_from_fixture

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def refuse_recovery_as_permission(*, treat_as_permit: bool) -> None:
    if treat_as_permit:
        raise LifecycleValidationError(
            REFUSED_RECOVERY_AS_PERMISSION,
            "recovery alignment cannot be treated as permission or authority",
        )


def refuse_process_kill(*, requested: bool) -> None:
    if requested and crr_forbid_process_kill():
        raise LifecycleValidationError(
            REFUSED_PROCESS_KILL,
            "process kill is forbidden in lifecycle first safe slice",
        )


def refuse_successor_spawn(*, requested: bool) -> None:
    if requested and crr_forbid_successor_spawn():
        raise LifecycleValidationError(
            REFUSED_SUCCESSOR_SPAWN,
            "successor spawning is forbidden in lifecycle first safe slice",
        )


def evaluate_alignment(
    record: RecoveryAlignmentRecord,
    *,
    observed_at: str,
    process_kill_requested: bool = False,
    successor_spawn_requested: bool = False,
) -> dict[str, object]:
    """Static CRR alignment evaluation; recovery is not permission."""
    if crr_static_fixtures_only() and process_kill_requested:
        refuse_process_kill(requested=True)
    if crr_static_fixtures_only() and successor_spawn_requested:
        refuse_successor_spawn(requested=True)
    if observed_at > record.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_ALIGNMENT,
            "alignment_id": record.alignment_id,
            "recovery_is_not_permission": True,
        }
    if crr_refuse_stale_alignment() and observed_at < record.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_ALIGNMENT,
            "alignment_id": record.alignment_id,
            "recovery_is_not_permission": True,
        }
    if record.recovery_active and record.source_module in {"msc", "ysr"}:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_RECOVERY_ACTIVE_CONFLICT,
            "alignment_id": record.alignment_id,
            "source_module": record.source_module,
            "recovery_is_not_permission": True,
        }
    if record.recovery_marker_ref and not record.snapshot_hash_ref and record.source_module == "els":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "crr.refused.snapshot_missing",
            "alignment_id": record.alignment_id,
            "recovery_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "aligned",
        "reason_code": "crr.advisory.alignment_recorded",
        "alignment_id": record.alignment_id,
        "source_module": record.source_module,
        "recovery_is_not_permission": True,
    }


def evaluate_fixture(
    fixture: Mapping[str, str],
    *,
    observed_at: str,
    process_kill_requested: bool = False,
    successor_spawn_requested: bool = False,
) -> dict[str, object]:
    record = alignment_from_fixture(dict(fixture))
    return evaluate_alignment(
        record,
        observed_at=observed_at,
        process_kill_requested=process_kill_requested,
        successor_spawn_requested=successor_spawn_requested,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "evaluate_alignment",
    "evaluate_fixture",
    "refuse_process_kill",
    "refuse_recovery_as_permission",
    "refuse_successor_spawn",
]
