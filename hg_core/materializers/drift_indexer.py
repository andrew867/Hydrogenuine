"""Control Surface Pack 6: Index DRIFT_SCORE_COMPUTED and DRIFT_SAFEGUARD_APPLIED to materialized views."""
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
        if action == "DRIFT_SCORE_COMPUTED":
            scores.append({
                **base,
                "drift_id": payload.get("drift_id"),
                "kind": payload.get("kind"),
                "thread_id": payload.get("thread_id"),
                "work_item_id": payload.get("work_item_id"),
                "score": payload.get("score"),
                "subject_ref": payload.get("subject_ref"),
                "factors": payload.get("factors", []),
            })
        elif action == "DRIFT_SAFEGUARD_APPLIED":
            alerts.append({
                **base,
                "safeguard_id": payload.get("safeguard_id"),
                "scope": payload.get("scope"),
                "effects": payload.get("effects", {}),
                "expiry_ts": payload.get("expiry_ts"),
                "rationale_artifact_id": payload.get("rationale_artifact_id"),
            })
    with open(root / "drift_scores.jsonl", "w", encoding="utf-8") as f:
        for r in scores:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "drift_alerts.jsonl", "w", encoding="utf-8") as f:
        for r in alerts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "drift", checkpoint)
