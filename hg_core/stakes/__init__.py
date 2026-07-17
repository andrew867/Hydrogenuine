"""
Sticky Reality stakes: agency_budget, trust_band, escrow, gating middleware.
"""

from .policy import load_policy, get_action_cost, get_trust_band_limits
from .gating import check_gate, GateResult

__all__ = ["load_policy", "get_action_cost", "get_trust_band_limits", "check_gate", "GateResult"]
