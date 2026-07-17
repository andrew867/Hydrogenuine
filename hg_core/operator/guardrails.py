"""
Control Surface Pack 7: Operator bias and fatigue controls — override budget, exception limits, quorum.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _materialized_root(workspace_root: Path) -> Path:
    return workspace_root / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# Default per-operator override budget (risk-weighted units); configurable.
DEFAULT_OVERRIDE_BUDGET = 100.0
DEFAULT_FATIGUE_OVERRIDES_PER_HOUR = 5


def check_override_budget(
    workspace_root: Path,
    operator_id: str,
    risk_weight: float = 1.0,
) -> Dict[str, Any]:
    """
    Check if operator has enough override budget. Returns { allowed: bool, remaining: float, reason: str }.
    """
    root = _materialized_root(workspace_root)
    path = root / "operator_guardrails.jsonl"
    debited = 0.0
    for row in _load_jsonl(path):
        if row.get("operator_id") == operator_id and row.get("action") == "OPERATOR_OVERRIDE_BUDGET_DEBITED":
            debited += float(row.get("risk_weight", 1.0))
    remaining = max(0.0, DEFAULT_OVERRIDE_BUDGET - debited)
    allowed = remaining >= risk_weight
    return {
        "allowed": allowed,
        "remaining": remaining,
        "reason": "" if allowed else "override_budget_exhausted",
    }


def debit_override_budget(
    *,
    operator_id: str,
    risk_weight: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    target_ref: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit OPERATOR_OVERRIDE_BUDGET_DEBITED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload: Dict[str, Any] = {
        "operator_id": operator_id,
        "risk_weight": risk_weight,
        "ts": ts,
    }
    if target_ref:
        payload["target_ref"] = target_ref
    return emit(
        "OPERATOR_OVERRIDE_BUDGET_DEBITED",
        "operator_guardrails",
        operator_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def check_fatigue_limit(
    workspace_root: Path,
    operator_id: str,
    overrides_per_hour_limit: int = DEFAULT_FATIGUE_OVERRIDES_PER_HOUR,
) -> Dict[str, Any]:
    """
    Check if operator is within fatigue throttle (overrides per hour). Returns { allowed: bool, count_last_hour: int }.
    """
    from datetime import timedelta
    root = _materialized_root(workspace_root)
    path = root / "operator_guardrails.jsonl"
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    count = 0
    for row in _load_jsonl(path):
        if row.get("operator_id") != operator_id:
            continue
        if row.get("action") == "OPERATOR_OVERRIDE_BUDGET_DEBITED":
            if (row.get("ts") or "") >= cutoff:
                count += 1
    allowed = count < overrides_per_hour_limit
    return {"allowed": allowed, "count_last_hour": count}


def record_steering_blocked(
    *,
    operator_id: str,
    reason: str,
    target_ref: Optional[Dict[str, Any]] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit STEERING_CHANGE_BLOCKED_BY_POLICY. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload: Dict[str, Any] = {"operator_id": operator_id, "reason": reason, "ts": ts}
    if target_ref:
        payload["target_ref"] = target_ref
    return emit(
        "STEERING_CHANGE_BLOCKED_BY_POLICY",
        "operator_guardrails",
        operator_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_steering_approved_by_quorum(
    *,
    operator_id: str,
    action_ref: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit STEERING_CHANGE_APPROVED_BY_QUORUM. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "STEERING_CHANGE_APPROVED_BY_QUORUM",
        "operator_guardrails",
        action_ref,
        {"operator_id": operator_id, "action_ref": action_ref, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def get_operator_guardrails_status(
    workspace_root: Path,
    operator_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Operator budgets and fatigue status from materialized operator_guardrails.jsonl."""
    root = _materialized_root(workspace_root)
    rows = _load_jsonl(root / "operator_guardrails.jsonl")
    if operator_id:
        rows = [r for r in rows if r.get("operator_id") == operator_id]
    # Enrich with computed remaining budget per operator
    by_op: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        op = r.get("operator_id") or "default"
        if op not in by_op:
            by_op[op] = {"operator_id": op, "override_debited": 0.0, "remaining_budget": DEFAULT_OVERRIDE_BUDGET}
        if r.get("action") == "OPERATOR_OVERRIDE_BUDGET_DEBITED":
            by_op[op]["override_debited"] = by_op[op].get("override_debited", 0) + float(r.get("risk_weight", 1.0))
    for op, data in by_op.items():
        data["remaining_budget"] = max(0.0, DEFAULT_OVERRIDE_BUDGET - data.get("override_debited", 0))
    return list(by_op.values())
