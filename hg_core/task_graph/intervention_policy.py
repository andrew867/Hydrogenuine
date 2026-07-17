"""
Intervention policy and behavior budgets (Autonomy Ch5 Phase 2).

Per docs/specs/intervention_policy.md: behavior budgets, intervention ladder,
deterministic enforcement when budget exceeded.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

INTERVENTION_STEPS = ["warn", "slowdown", "constrain", "sandbox", "escalate", "halt"]
STEPS_BLOCKING_EXTERNAL_WRITES = frozenset({"sandbox", "escalate", "halt"})


def default_budgets() -> Dict[str, int]:
    """Default behavior budget limits."""
    return {
        "max_delegation_depth": 15,
        "max_active_work_items": 100,
        "max_splits_per_run": 50,
        "max_handoffs_per_run": 80,
        "max_rework_edits_per_artifact": 10,
        "max_anomalies_per_run": 20,
    }


def which_budget_exceeded(
    metrics: Dict[str, Any],
    budgets: Optional[Dict[str, int]] = None,
) -> Optional[str]:
    """Return the first budget key that is exceeded, or None."""
    budgets = budgets or default_budgets()
    depth = metrics.get("delegation_depth_max", 0)
    if depth > budgets.get("max_delegation_depth", 999):
        return "max_delegation_depth"
    total = metrics.get("total_work_items", 0)
    if total > budgets.get("max_active_work_items", 999):
        return "max_active_work_items"
    splits = metrics.get("split_count", 0)
    if splits > budgets.get("max_splits_per_run", 999):
        return "max_splits_per_run"
    handoffs = metrics.get("handoff_count", 0)
    if handoffs > budgets.get("max_handoffs_per_run", 999):
        return "max_handoffs_per_run"
    rework = metrics.get("rework_rate", 0)
    if isinstance(rework, (int, float)) and rework > budgets.get("max_rework_edits_per_artifact", 999):
        return "max_rework_edits_per_artifact"
    anomalies = len(metrics.get("anomalies", []))
    if anomalies > budgets.get("max_anomalies_per_run", 999):
        return "max_anomalies_per_run"
    return None


def intervention_step_for_budget(
    budget_key: str,
    severity: str = "warn",
) -> str:
    """Map exceeded budget to intervention step. Deterministic."""
    if budget_key in ("max_delegation_depth", "max_active_work_items"):
        return "constrain"
    if budget_key == "max_anomalies_per_run":
        return "escalate"
    if budget_key == "max_rework_edits_per_artifact":
        return "slowdown"
    return "warn"


def current_intervention(
    metrics: Dict[str, Any],
    budgets: Optional[Dict[str, int]] = None,
    anomalies: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Return { step, exceeded_budget, recorded }.
    step is one of INTERVENTION_STEPS; when a budget is exceeded, step is deterministic and recorded.
    """
    budgets = budgets or default_budgets()
    exceeded = which_budget_exceeded(metrics, budgets)
    if not exceeded:
        return {"step": "warn", "exceeded_budget": None, "recorded": True}
    step = intervention_step_for_budget(exceeded)
    return {"step": step, "exceeded_budget": exceeded, "recorded": True}


def should_block_external_writes(
    intervention_step: str,
    degraded: bool,
) -> bool:
    """True if external writes should be blocked (sandbox/escalate/halt or degraded)."""
    if degraded:
        return True
    return intervention_step in STEPS_BLOCKING_EXTERNAL_WRITES
