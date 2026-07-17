"""
Load trust_and_budget policy artifact; resolve action costs and trust band rules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:
    yaml = None


def _default_policy() -> Dict[str, Any]:
    return {
        "action_costs": {"READ": 0.1, "WRITE": 1.0, "DECISION_COMMITTED": 1.0},
        "trust_bands": [{"name": "band_0", "max_action": "READ"}, {"name": "band_1", "max_action": "WRITE"}],
        "budget": {"default_limit": 100.0, "hard": True},
        "escrow": {"high_impact_actions": ["DECISION_COMMITTED"], "lock_amount_default": 10.0},
    }


def load_policy(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    if workspace_root is None:
        try:
            from hg_lib.config import get_workspace_root
            workspace_root = get_workspace_root()
        except ImportError:
            return _default_policy()
    path = Path(workspace_root) / "artifacts" / "policy" / "trust_and_budget_policy.yaml"
    if not path.exists() or yaml is None:
        return _default_policy()
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or _default_policy()
    except Exception:
        return _default_policy()


def get_action_cost(policy: Dict[str, Any], action: str) -> float:
    costs = (policy or {}).get("action_costs") or {}
    return float(costs.get(action, 1.0))


def get_trust_band_limits(policy: Dict[str, Any]) -> Dict[int, Optional[str]]:
    """Return band index -> max_action (or None for full)."""
    bands = (policy or {}).get("trust_bands") or []
    out = {}
    for i, b in enumerate(bands):
        out[i] = b.get("max_action")
    return out
