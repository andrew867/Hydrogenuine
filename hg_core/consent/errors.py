"""Consent enforcement errors."""
from __future__ import annotations


class ConsentDeniedError(PermissionError):
    """Raised when user-targeted recognition is attempted without valid consent."""

    def __init__(self, subject_id: str, reason: str = "consent_required") -> None:
        self.subject_id = subject_id
        self.reason = reason
        super().__init__(f"consent denied for {subject_id}: {reason}")
