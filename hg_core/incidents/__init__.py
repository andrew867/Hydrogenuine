"""
OS Phase 2: Incident lifecycle enforcement hooks.
ENFORCEMENT_APPLIED (what changed, why, references); AUTONOMY_RESTORED (after postmortem gate).
"""

from .enforcement import apply_enforcement, record_autonomy_restored

__all__ = ["apply_enforcement", "record_autonomy_restored"]
