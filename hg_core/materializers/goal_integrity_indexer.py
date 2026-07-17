"""Control Surface Pack 7: Index GOAL_INTEGRITY events to scores and alerts."""
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
    scores: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        base = {"event_id": ev.get("event_id"), "ts": ev.get("ts", ""), "scope_type": scope_type, "scope_id": scope_id}
        if action == "GOAL_INTEGRITY_SCORE_COMPUTED":
            scores.append({
                **base,
                "gi_id": payload.get("gi_id"),
                "target_ref": payload.get("target_ref"),
                "work_item_id": payload.get("work_item_id"),
                "score": payload.get("score"),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
                "factors": payload.get("factors", []),
                "evidence_refs": payload.get("evidence_refs", []),
            })
        elif action == "GOAL_INTEGRITY_ALERT_RAISED":
            alerts.append({
                **base,
                "target_ref": payload.get("target_ref"),
                "work_item_id": payload.get("work_item_id"),
                "reason": payload.get("reason", ""),
            })

    with open(root / "goal_integrity_scores.jsonl", "w", encoding="utf-8") as f:
        for r in scores:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "goal_integrity_alerts.jsonl", "w", encoding="utf-8") as f:
        for r in alerts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "goal_integrity", checkpoint)
