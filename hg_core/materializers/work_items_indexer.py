"""
OS Phase 1: Work items indexer. Builds current state per work item from WORK_ITEM_* events.
Output: work_items.jsonl (current snapshot per work_item_id).
"""
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
    state: Dict[str, Dict[str, Any]] = {}
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        work_item_id = payload.get("work_item_id")
        if not work_item_id:
            continue
        if work_item_id not in state:
            state[work_item_id] = {
                "work_item_id": work_item_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "status": "proposed",
                "updated_ts": ts,
            }
        s = state[work_item_id]
        s["updated_ts"] = ts
        if action == "WORK_ITEM_CREATED":
            s["type"] = payload.get("type", "task")
            s["title"] = payload.get("title", "")
            s["description"] = payload.get("description", "")
            s["created_ts"] = payload.get("created_ts", ts)
            s["priority"] = payload.get("priority", "normal")
            s["status"] = payload.get("status", "proposed")
        elif action == "WORK_ITEM_UPDATED":
            changes = payload.get("changes") or {}
            for k, v in changes.items():
                s[k] = v
        elif action == "WORK_ITEM_ASSIGNED":
            s["owner_agent_id"] = payload.get("owner_agent_id", "")
        elif action == "WORK_ITEM_BLOCKED":
            s["status"] = "blocked"
        elif action == "WORK_ITEM_UNBLOCKED":
            if s.get("status") == "blocked":
                s["status"] = "active"
        elif action == "WORK_ITEM_CLOSED":
            s["status"] = payload.get("status", "done")

    with open(root / "work_items.jsonl", "w", encoding="utf-8") as f:
        for wi in state.values():
            f.write(json.dumps(wi, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "work_items", checkpoint)
