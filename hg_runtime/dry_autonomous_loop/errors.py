"""Dry autonomous loop errors."""


class DryAutonomousLoopError(Exception):
    """Base dry autonomous loop error."""


class DryAutonomousLoopConfigError(DryAutonomousLoopError):
    """Invalid loop configuration."""


class DryAutonomousLoopLockError(DryAutonomousLoopError):
    """Loop lock failure."""


class DryAutonomousLoopRunnerError(DryAutonomousLoopError):
    """Loop runner failure."""


class DryAutonomousLoopStopPanicError(DryAutonomousLoopError):
    """STOP/PANIC control failure."""


class DryAutonomousLoopPostflightError(DryAutonomousLoopError):
    """Postflight verification failure."""


__all__ = [
    "DryAutonomousLoopConfigError",
    "DryAutonomousLoopError",
    "DryAutonomousLoopLockError",
    "DryAutonomousLoopPostflightError",
    "DryAutonomousLoopRunnerError",
    "DryAutonomousLoopStopPanicError",
]
