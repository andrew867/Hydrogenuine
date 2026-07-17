"""Extended dry autonomy errors."""


class ExtendedDryAutonomyError(Exception):
    """Base extended dry autonomy error."""


class ExtendedDryAutonomyConfigError(ExtendedDryAutonomyError, ValueError):
    """Invalid extended dry autonomy configuration."""


class ExtendedDryAutonomyLockError(ExtendedDryAutonomyError, RuntimeError):
    """Extended loop lock failure."""


class ExtendedDryAutonomyRunnerError(ExtendedDryAutonomyError, RuntimeError):
    """Extended loop runner failure."""


class ExtendedDryAutonomyCheckpointError(ExtendedDryAutonomyError, RuntimeError):
    """Checkpoint verification failure."""


class ExtendedDryAutonomyPauseResumeError(ExtendedDryAutonomyError, RuntimeError):
    """Pause/resume control failure."""


class ExtendedDryAutonomyPostflightError(ExtendedDryAutonomyError, RuntimeError):
    """Postflight verification failure."""


class EnduranceBudgetExceeded(ExtendedDryAutonomyError, RuntimeError):
    def __init__(self, verdict: str) -> None:
        super().__init__(verdict)
        self.verdict = verdict


__all__ = [
    "EnduranceBudgetExceeded",
    "ExtendedDryAutonomyCheckpointError",
    "ExtendedDryAutonomyConfigError",
    "ExtendedDryAutonomyError",
    "ExtendedDryAutonomyLockError",
    "ExtendedDryAutonomyPauseResumeError",
    "ExtendedDryAutonomyPostflightError",
    "ExtendedDryAutonomyRunnerError",
]
