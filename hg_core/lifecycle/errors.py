"""Lifecycle validation errors — cycles are not permission."""

from __future__ import annotations

REFUSED_RECOVERY_AS_PERMISSION = "crr.refused.recovery_as_permission"
REFUSED_STALE_ALIGNMENT = "crr.refused.stale_alignment"
REFUSED_EXPIRED_ALIGNMENT = "crr.refused.expired_alignment"
REFUSED_RECOVERY_ACTIVE_CONFLICT = "crr.refused.recovery_active_conflict"
REFUSED_SUCCESSOR_SPAWN = "crr.refused.successor_spawn"
REFUSED_PROCESS_KILL = "crr.refused.process_kill"

REFUSED_FINAL_MESSAGE_AS_COMMAND = "mor.refused.final_message_as_command"
REFUSED_GHOST_AUTHORITY = "mor.refused.ghost_authority"
REFUSED_FORBIDDEN_SUCCESSOR_INHERITANCE = "mor.refused.forbidden_successor_inheritance"
REFUSED_STALE_DEATH_NOTICE = "mor.refused.stale_death_notice"
REFUSED_EXPIRED_DEATH_NOTICE = "mor.refused.expired_death_notice"

REFUSED_IDENTITY_CONTINUITY = "cnt.refused.identity_continuity"
REFUSED_STALE_AUTHORITY_INHERITANCE = "cnt.refused.stale_authority_inheritance"
REFUSED_EXPIRED_CONTINUITY_CLAIM = "cnt.refused.expired_continuity_claim"
REFUSED_STALE_CONTINUITY_CLAIM = "cnt.refused.stale_continuity_claim"


class LifecycleValidationError(ValueError):
    """Raised when lifecycle records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "LifecycleValidationError",
    "REFUSED_EXPIRED_ALIGNMENT",
    "REFUSED_EXPIRED_CONTINUITY_CLAIM",
    "REFUSED_EXPIRED_DEATH_NOTICE",
    "REFUSED_FINAL_MESSAGE_AS_COMMAND",
    "REFUSED_FORBIDDEN_SUCCESSOR_INHERITANCE",
    "REFUSED_GHOST_AUTHORITY",
    "REFUSED_IDENTITY_CONTINUITY",
    "REFUSED_PROCESS_KILL",
    "REFUSED_RECOVERY_ACTIVE_CONFLICT",
    "REFUSED_RECOVERY_AS_PERMISSION",
    "REFUSED_STALE_ALIGNMENT",
    "REFUSED_STALE_AUTHORITY_INHERITANCE",
    "REFUSED_STALE_CONTINUITY_CLAIM",
    "REFUSED_STALE_DEATH_NOTICE",
    "REFUSED_SUCCESSOR_SPAWN",
]
