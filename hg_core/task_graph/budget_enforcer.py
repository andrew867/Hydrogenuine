"""Budget enforcement (MVP)."""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from .effects import get_budgets

BUDGET_EXCEEDED_CODE = "BUDGET_EXCEEDED"


def check_before_dispatch(
    run_policy: Dict[str, Any], run_state: Dict[str, Any], cost: Dict[str, float]
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Return (True, None) if projected usage is within limits; else (False, error_dict)."""
    budgets = get_budgets(run_policy)
    used = run_state.setdefault("budget_used", {})
    for k, c in (cost or {}).items():
        if k in budgets:
            lim = budgets[k].limit
            nxt = float(used.get(k, 0.0)) + float(c)
            if nxt > lim and budgets[k].hard:
                return False, {
                    "code": BUDGET_EXCEEDED_CODE,
                    "budget": k,
                    "limit": lim,
                    "would_be": nxt,
                }
    return True, None


def apply_after_dispatch(
    run_policy: Dict[str, Any], run_state: Dict[str, Any], observed: Dict[str, float]
) -> None:
    """Increment run_state['budget_used'] by observed usage."""
    used = run_state.setdefault("budget_used", {})
    for k, v in (observed or {}).items():
        used[k] = float(used.get(k, 0.0)) + float(v)
