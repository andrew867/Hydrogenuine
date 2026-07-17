"""Supervised rehearsal errors."""


class RehearsalError(Exception):
    """Base rehearsal error."""


class RehearsalConfigError(RehearsalError):
    """Invalid rehearsal configuration."""


class RehearsalLockError(RehearsalError):
    """Run lock failure."""


class RehearsalStopPanicError(RehearsalError):
    """STOP/PANIC control failure."""


class RehearsalRunnerError(RehearsalError):
    """Rehearsal runner failure."""


class PostflightError(RehearsalError):
    """Postflight verification failure."""


__all__ = [
    "PostflightError",
    "RehearsalConfigError",
    "RehearsalError",
    "RehearsalLockError",
    "RehearsalRunnerError",
    "RehearsalStopPanicError",
]
