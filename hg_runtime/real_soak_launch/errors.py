"""Real soak launch errors."""

from __future__ import annotations


class RealSoakLaunchError(Exception):
    pass


class EnvelopeValidationError(RealSoakLaunchError):
    pass


class LivePostGuardError(RealSoakLaunchError):
    pass
