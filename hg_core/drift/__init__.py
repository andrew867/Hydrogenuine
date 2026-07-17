"""
Control Surface Pack 6: Orthogonal ghost drift detection.
"""
from .features import extract_drift_features
from .scoring import compute_drift_scores, emit_drift_score
from .safeguards import apply_drift_safeguard, list_active_safeguards
from .api import get_drift_scores, get_drift_alerts, preflight_drift

__all__ = [
    "extract_drift_features",
    "compute_drift_scores",
    "emit_drift_score",
    "apply_drift_safeguard",
    "list_active_safeguards",
    "get_drift_scores",
    "get_drift_alerts",
    "preflight_drift",
]
