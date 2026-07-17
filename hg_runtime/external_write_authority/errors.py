"""External write authority errors."""

from __future__ import annotations


class ExternalWriteAuthorityError(Exception):
    """Base external write authority error."""


class ExternalWriteAuthorityDenied(ExternalWriteAuthorityError):
    """Authority denied — produces refusal receipt."""


class ExternalWriteLiveDispatchForbidden(ExternalWriteAuthorityError):
    """Live dispatch attempted in Phase 17 — RED."""


class ExternalWriteScopeViolation(ExternalWriteAuthorityError):
    """Scope/platform/action mismatch."""
