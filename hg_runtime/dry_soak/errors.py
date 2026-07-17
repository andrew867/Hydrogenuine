"""Dry soak errors."""


class DrySoakError(Exception):
    """Base dry soak error."""


class DrySoakConfigError(DrySoakError):
    """Invalid dry soak configuration."""


class DrySoakRunnerError(DrySoakError):
    """Dry soak runner failure."""


class FailureBudgetExceeded(DrySoakRunnerError):
    """Failure budget exceeded."""

    def __init__(self, verdict: str):
        super().__init__(verdict)
        self.verdict = verdict


__all__ = ["DrySoakConfigError", "DrySoakError", "DrySoakRunnerError", "FailureBudgetExceeded"]
