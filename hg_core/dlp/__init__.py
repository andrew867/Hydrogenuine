"""
OS Phase 5: Data governance, DLP scanning, quarantine, legal holds.
"""

from .scanner import (
    run_dlp_scan,
    quarantine_artifact,
    release_from_quarantine,
    apply_legal_hold,
    release_legal_hold,
    record_key_rotated,
)

__all__ = [
    "run_dlp_scan",
    "quarantine_artifact",
    "release_from_quarantine",
    "apply_legal_hold",
    "release_legal_hold",
    "record_key_rotated",
]
