"""Control Surface Pack 7: Index steering directive events to steering_directives, steering_active, steering_timeline."""
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
    directives: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    active_by_target: Dict[str, Dict[str, Any]] = {}
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        base = {"event_id": ev.get("event_id"), "ts": ts, "scope_type": scope_type, "scope_id": scope_id}

        if action == "STEERING_DIRECTIVE_PUBLISHED":
            directives.append({
                **base,
                "directive_id": payload.get("directive_id"),
                "target_ref": payload.get("target_ref"),
                "goal": payload.get("goal"),
                "constraints": payload.get("constraints", []),
                "autonomy_preset": payload.get("autonomy_preset"),
                "issued_ts": payload.get("issued_ts"),
                "expires_ts": payload.get("expires_ts"),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
                "version": payload.get("version"),
                "supersedes": payload.get("supersedes", ""),
            })
            target_ref = payload.get("target_ref") or {}
            target_id = (target_ref.get("id") or "") or "default"
            timeline.append({**base, "action": action, "payload": payload, "target_ref": target_ref})
        elif action == "STEERING_DIRECTIVE_APPLIED":
            target_ref = payload.get("target_ref") or {}
            target_id = (target_ref.get("id") or "") or "default"
            active_by_target[target_id] = {
                "target_ref": target_ref,
                "directive_id": payload.get("directive_id"),
                "ts": ts,
            }
            timeline.append({**base, "action": action, "payload": payload, "target_ref": target_ref})
        elif action == "STEERING_DIRECTIVE_SUPERSEDED":
            timeline.append({**base, "action": action, "payload": payload})

    with open(root / "steering_directives.jsonl", "w", encoding="utf-8") as f:
        for r in directives:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "steering_active.jsonl", "w", encoding="utf-8") as f:
        for r in active_by_target.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "steering_timeline.jsonl", "w", encoding="utf-8") as f:
        for r in timeline:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "steering_state", checkpoint)
