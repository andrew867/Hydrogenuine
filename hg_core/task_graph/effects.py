"""Effect counters and helpers (MVP)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Budget:
    limit: float
    hard: bool = True
    on_exceed: str = "fail_run"  # fail_run|fail_node|pause|escalate
    scope: str = "run"  # run|node


def get_budgets(run_policy: Dict[str, Any]) -> Dict[str, Budget]:
    """Parse run_policy['budgets'] into a dict of Budget instances."""
    raw = run_policy.get("budgets") or {}
    out: Dict[str, Budget] = {}
    for k, v in raw.items():
        out[k] = Budget(
            limit=float(v.get("limit")),
            hard=bool(v.get("hard", True)),
            on_exceed=v.get("on_exceed", "fail_run"),
            scope=v.get("scope", "run"),
        )
    return out
