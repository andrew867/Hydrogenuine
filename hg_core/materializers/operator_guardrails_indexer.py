"""Control Surface Pack 7: Index operator guardrails events to operator_guardrails.jsonl."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, save_checkpoint


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        base = {"event_id": ev.get("event_id"), "ts": ev.get("ts", ""), "scope_type": scope_type, "scope_id": scope_id}

        if action == "OPERATOR_OVERRIDE_BUDGET_DEBITED":
            rows.append({
                **base,
                "action": action,
                "operator_id": payload.get("operator_id", ""),
                "risk_weight": payload.get("risk_weight", 1.0),
                "target_ref": payload.get("target_ref"),
            })
        elif action == "OPERATOR_FATIGUE_LIMIT_REACHED":
            rows.append({
                **base,
                "action": action,
                "operator_id": payload.get("operator_id", ""),
            })
        elif action == "STEERING_CHANGE_BLOCKED_BY_POLICY":
            rows.append({
                **base,
                "action": action,
                "operator_id": payload.get("operator_id", ""),
                "reason": payload.get("reason", ""),
                "target_ref": payload.get("target_ref"),
            })
        elif action == "STEERING_CHANGE_APPROVED_BY_QUORUM":
            rows.append({
                **base,
                "action": action,
                "operator_id": payload.get("operator_id", ""),
                "action_ref": payload.get("action_ref", ""),
            })

    with open(root / "operator_guardrails.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "operator_guardrails", checkpoint)
