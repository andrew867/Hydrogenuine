"""
Viz Phase 3: Trust and policy views (bands, budget, escrow, gating) — read-only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.stakes.policy import load_policy, get_trust_band_limits
from hg_core.operator.guardrails import get_operator_guardrails_status


def adapt_trust_bands(workspace_root: Path) -> List[Dict[str, Any]]:
    """Return trust bands from stakes policy: list of { band_index, name, max_action }."""
    root = Path(workspace_root)
    policy = load_policy(root)
    bands = (policy.get("trust_bands") or [])
    limits = get_trust_band_limits(policy)
    out: List[Dict[str, Any]] = []
    for i, b in enumerate(bands):
        out.append({
            "band_index": i,
            "name": b.get("name", f"band_{i}"),
            "max_action": b.get("max_action") or limits.get(i),
        })
    return out


def adapt_budget_view(workspace_root: Path) -> Dict[str, Any]:
    """Return budget view: policy budget (default_limit, hard) and operator budgets (remaining, override_debited)."""
    root = Path(workspace_root)
    policy = load_policy(root)
    budget_cfg = policy.get("budget") or {}
    operator_budgets = get_operator_guardrails_status(root)
    return {
        "policy_budget": {
            "default_limit": float(budget_cfg.get("default_limit", 100.0)),
            "hard": bool(budget_cfg.get("hard", True)),
        },
        "operator_budgets": operator_budgets,
    }


def adapt_escrow_view(workspace_root: Path) -> Dict[str, Any]:
    """Return escrow view from policy: lock_amount_default, high_impact_actions."""
    root = Path(workspace_root)
    policy = load_policy(root)
    escrow = policy.get("escrow") or {}
    return {
        "lock_amount_default": float(escrow.get("lock_amount_default", 10.0)),
        "high_impact_actions": list(escrow.get("high_impact_actions") or []),
    }


def adapt_gating_view(workspace_root: Path) -> Dict[str, Any]:
    """Return gating view: trust_band_limits, require_approval_for_actions, high_impact_actions (escrow)."""
    root = Path(workspace_root)
    policy = load_policy(root)
    band_limits = get_trust_band_limits(policy)
    require_approval = list(policy.get("require_approval_for_actions") or [])
    escrow = policy.get("escrow") or {}
    high_impact = list(escrow.get("high_impact_actions") or [])
    return {
        "trust_band_limits": {str(k): v for k, v in band_limits.items()},
        "require_approval_for_actions": require_approval,
        "high_impact_actions": high_impact,
    }
