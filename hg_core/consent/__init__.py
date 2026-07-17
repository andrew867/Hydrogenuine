"""Cognitive recognition consent ledger and enforcement (G15)."""
from .errors import ConsentDeniedError
from .ledger import ConsentLedger
from .resolver import assert_recognition_consent, is_consent_surface_enabled, resolve_consent_class

__all__ = [
    "ConsentDeniedError",
    "ConsentLedger",
    "resolve_consent_class",
    "assert_recognition_consent",
    "is_consent_surface_enabled",
]
