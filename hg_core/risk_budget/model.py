"""
Semantic Risk Budget: impact_cost from action class, asset criticality, reversibility, fan-out, environment.
Budget debit; insufficient budget triggers approval/scope reduction/deny (emit BUDGET_INSUFFICIENT).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# Action class cost base (higher = more impact)
ACTION_CLASS_COST: Dict[str, float] = {
    "READ": 0.5,
    "WRITE": 2.0,
    "ARTIFACT_PUBLISH": 1.5,
    "DECISION_PROPOSED": 1.0,
    "DECISION_COMMITTED": 2.0,
    "RUN_START": 1.0,
    "RUN_END": 0.5,
    "default": 1.0,
}

# Environment multiplier (prod = highest risk)
ENV_MULTIPLIER: Dict[str, float] = {
    "dev": 0.5,
    "staging": 0.8,
    "prod": 1.0,
    "default": 1.0,
}


def compute_impact_cost(
    *,
    action_class: str = "default",
    asset_criticality: float = 1.0,
    reversibility: float = 1.0,
    fan_out: float = 1.0,
    environment: str = "default",
) -> float:
    """
    Compute impact_cost for gating. Higher = more impact.
    reversibility: 1 = reversible, 0 = irreversible (increases cost).
    fan_out: number of dependent items or 1.0 for single.
    """
    base = ACTION_CLASS_COST.get(action_class) or ACTION_CLASS_COST["default"]
    env = ENV_MULTIPLIER.get(environment) or ENV_MULTIPLIER["default"]
    # Irreversibility increases cost: 1 + (1 - reversibility)
    irrev = 1.0 + (1.0 - max(0.0, min(1.0, reversibility)))
    cost = base * asset_criticality * irrev * max(1.0, fan_out) * env
    return round(cost, 2)


def _get_scope_key(scope: Dict[str, str]) -> str:
    t = scope.get("type") or "global"
    i = scope.get("id") or "default"
    return f"{t}/{i}"


def _compute_balance_from_ledger(workspace_root: Path, scope_key: str) -> Tuple[float, float, float, Optional[str]]:
    """Return (current_balance, total_debited, initial_balance, last_event_id). Balance = initial - total_debited."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    initial = 0.0
    total_debited = 0.0
    last_id: Optional[str] = None
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ev_scope = ev.get("scope") or {}
        sk = _get_scope_key(ev_scope)
        if sk != scope_key:
            continue
        if action == "BUDGET_INITIALIZED":
            initial = float(payload.get("initial_balance", 0))
            last_id = ev.get("event_id")
        elif action == "BUDGET_DEBITED":
            total_debited += float(payload.get("amount", 0))
            last_id = ev.get("event_id")
    return initial - total_debited, total_debited, initial, last_id


def init_budget(
    *,
    initial_balance: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit BUDGET_INITIALIZED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "BUDGET_INITIALIZED",
        "risk_budget",
        "init_" + hashlib.sha256(f"{_get_scope_key(scope)}:{ts}".encode()).hexdigest()[:12],
        {"initial_balance": initial_balance, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def get_budget_status(
    workspace_root: Path,
    scope: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Return current budget status for scope. If scope is None, use first scope found with budget.
    Returns: balance, total_debited, initial_balance (if known), scope_key.
    """
    workspace_root = Path(workspace_root)
    if scope is None:
        scope = {"type": "global", "id": "default"}
    scope_key = _get_scope_key(scope)
    balance, total_debited, initial, _ = _compute_balance_from_ledger(workspace_root, scope_key)
    return {
        "balance": balance,
        "total_debited": total_debited,
        "initial_balance": initial,
        "scope_key": scope_key,
    }


def check_budget_sufficient(
    amount: float,
    workspace_root: Path,
    scope: Optional[Dict[str, str]] = None,
) -> bool:
    """Return True if current balance >= amount."""
    st = get_budget_status(workspace_root, scope=scope)
    return st["balance"] >= amount


def debit_budget(
    *,
    amount: float,
    action_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    impact_cost_params: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """
    Debit amount from budget. If insufficient, emit BUDGET_INSUFFICIENT and return (False, event_id).
    Otherwise emit BUDGET_DEBITED and return (True, event_id).
    If impact_cost_params is provided, amount can be computed via compute_impact_cost(**impact_cost_params).
    """
    workspace_root = Path(workspace_root or ".")
    if impact_cost_params:
        amount = compute_impact_cost(**impact_cost_params)
    scope_key = _get_scope_key(scope)
    balance, _, _, _ = _compute_balance_from_ledger(workspace_root, scope_key)
    ts = _iso_ts()
    if balance < amount:
        event_id = emit(
            "BUDGET_INSUFFICIENT",
            "risk_budget",
            action_id,
            {
                "action_id": action_id,
                "amount": amount,
                "balance_before": balance,
                "ts": ts,
            },
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, event_id
    event_id = emit(
        "BUDGET_DEBITED",
        "risk_budget",
        action_id,
        {
            "action_id": action_id,
            "amount": amount,
            "balance_after": balance - amount,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True, event_id
