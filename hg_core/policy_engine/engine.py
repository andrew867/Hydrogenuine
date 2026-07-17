"""
PolicyEngine: load YAML policy, evaluate(context) -> allow, require_approval, cost_multiplier, tool_allowlist, rationale.
Uses trust_bands (max_action per band), action_costs, optional require_approval_for_actions, tool_allowlist.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


class PolicyEngine:
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy or {}

    @staticmethod
    def load(path: str) -> "PolicyEngine":
        path = Path(path)
        if not path.exists() or yaml is None:
            return PolicyEngine({})
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return PolicyEngine(data)

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        ctx: action, trust_band (int), agency_budget (float), tool_name (optional), escrow_locked (optional).
        Returns: allow (bool), require_approval (bool), cost_multiplier (float), tool_allowlist (list), rationale (dict).
        """
        action = ctx.get("action", "")
        trust_band = int(ctx.get("trust_band", 0))
        agency_budget = float(ctx.get("agency_budget", 0.0))
        tool_name = ctx.get("tool_name", "")
        bands = (self.policy.get("trust_bands") or [])
        band_limits: Dict[int, Optional[str]] = {}
        for i, b in enumerate(bands):
            band_limits[i] = b.get("max_action")
        max_action = band_limits.get(trust_band) if trust_band < len(bands) else None
        action_costs = (self.policy.get("action_costs") or {})
        cost = float(action_costs.get(action, 1.0))
        budget = (self.policy.get("budget") or {})
        default_limit = float(budget.get("default_limit", 100.0))
        hard = budget.get("hard", True)
        allow = True
        rationale: Dict[str, Any] = {"band": trust_band, "max_action": max_action, "cost": cost}
        if max_action is not None and action:
            order = ["READ", "WRITE", "ARTIFACT_PUBLISH", "DECISION_PROPOSED", "DECISION_COMMITTED", "RUN_START", "RUN_END"]
            try:
                ai = order.index(action) if action in order else 999
                mi = order.index(max_action) if max_action in order else 999
                if ai > mi:
                    allow = False
                    rationale["deny_reason"] = "trust_band_insufficient"
            except ValueError:
                pass
        if allow and hard and agency_budget < cost:
            allow = False
            rationale["deny_reason"] = "budget_insufficient"
        require_approval = False
        approval_actions = (self.policy.get("require_approval_for_actions") or [])
        if action in approval_actions:
            require_approval = True
            rationale["require_approval_reason"] = "policy"
        escrow = self.policy.get("escrow") or {}
        high_impact = escrow.get("high_impact_actions") or []
        if action in high_impact:
            require_approval = True
            rationale["require_approval_reason"] = "high_impact_escrow"
        tool_allowlist: List[str] = []
        per_band = (self.policy.get("tool_allowlist_per_band") or {})
        key = str(trust_band)
        if key in per_band:
            tool_allowlist = list(per_band[key]) if isinstance(per_band[key], (list, tuple)) else []
        if tool_name and tool_allowlist and tool_name not in tool_allowlist:
            allow = False
            rationale["deny_reason"] = "tool_not_allowlisted"
        cost_multiplier = 1.0
        if "cost_multipliers" in self.policy and isinstance(self.policy["cost_multipliers"], dict):
            cost_multiplier = float(self.policy["cost_multipliers"].get(action, 1.0))
        return {
            "allow": allow,
            "require_approval": require_approval,
            "cost_multiplier": cost_multiplier,
            "tool_allowlist": tool_allowlist,
            "rationale": rationale,
        }

    def simulate(self, scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run evaluate on each scenario; return list of results (for simulation endpoint)."""
        return [self.evaluate(s) for s in scenarios]
