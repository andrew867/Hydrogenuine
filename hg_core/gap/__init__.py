"""
Differentiators Pack 2: Reality gap measurement.
Gap score (model vs world), GAP_ALERT_RAISED, GAP_CONTROL_APPLIED.
"""

from .layer import (
    compute_gap_score,
    raise_gap_alert,
    apply_gap_control,
    get_gap_scores,
)

__all__ = [
    "compute_gap_score",
    "raise_gap_alert",
    "apply_gap_control",
    "get_gap_scores",
]
