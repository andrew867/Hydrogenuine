"""
Regulatory policy artifact: load YAML with version and effective-date resolution.
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
        "version": "1.0",
        "effective_from": "2020-01-01T00:00:00Z",
        "state_dimensions": ["trust_band", "agency_budget", "escrow_locked", "incident_points"],
        "modulation_rules": [],
    }


def load_regulatory_policy(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load regulatory policy from artifacts/policy/regulatory_policy.yaml; fallback to default."""
    workspace_root = Path(workspace_root or ".")
    path = workspace_root / "artifacts" / "policy" / "regulatory_policy.yaml"
    if not path.exists() or yaml is None:
        return _default_policy()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else _default_policy()
    except Exception:
        return _default_policy()


def get_effective_policy_at(workspace_root: Path, at_ts: str) -> Dict[str, Any]:
    """Return policy effective at at_ts (by effective_from). If multiple versions, return latest with effective_from <= at_ts."""
    policy = load_regulatory_policy(workspace_root)
    effective = policy.get("effective_from", "")
    if effective and at_ts and effective > at_ts:
        return _default_policy()
    return policy
