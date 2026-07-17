"""Overnight field run errors."""

from __future__ import annotations


class OvernightFieldRunError(Exception):
    pass


class FieldRunConfigError(OvernightFieldRunError):
    pass


class FieldRunLockError(OvernightFieldRunError):
    pass


class FieldRunContinuityError(OvernightFieldRunError):
    pass
