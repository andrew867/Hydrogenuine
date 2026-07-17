"""
Differentiators Pack 1: Coalition detection.
Pack 3: Coalition safeguards (apply/lift from signals).
"""

from .signals import (
    detect_coalition_signals,
    list_coalition_signals,
)
from .safeguards import (
    apply_safeguard,
    lift_safeguard,
    apply_safeguards_for_signal,
    list_active_safeguards,
)

__all__ = [
    "detect_coalition_signals",
    "list_coalition_signals",
    "apply_safeguard",
    "lift_safeguard",
    "apply_safeguards_for_signal",
    "list_active_safeguards",
]
