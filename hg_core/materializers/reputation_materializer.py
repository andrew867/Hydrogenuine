"""
Reputation and agent state materializer from EVALUATION_RECORDED, ESCROW_*, TRUST_BAND_CHANGED, BUDGET_ADJUSTED.
Output: reputation_timeseries.jsonl, agent_state_snapshots.jsonl. Supports incremental (rebuild=False).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, load_checkpoint, save_checkpoint


def _state_path(root: Path) -> Path:
    return root / "reputation_state.json"


def _load_state(root: Path) -> Optional[tuple]:
    path = _state_path(root)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    timeseries = data.get("timeseries")
    snapshots = data.get("snapshots")
    agent_state = data.get("agent_state")
    checkpoint = data.get("checkpoint")
    if not isinstance(timeseries, list) or not isinstance(snapshots, list):
        return None
    if not isinstance(agent_state, dict) or not isinstance(checkpoint, dict):
        return None
    return (timeseries, snapshots, agent_state, checkpoint)


def _save_state(
    root: Path,
    timeseries: List[Dict[str, Any]],
    snapshots: List[Dict[str, Any]],
    agent_state: Dict[str, Dict[str, Any]],
    checkpoint: Dict[str, str],
) -> None:
    path = _state_path(root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"timeseries": timeseries, "snapshots": snapshots, "agent_state": agent_state, "checkpoint": checkpoint},
            f,
            ensure_ascii=False,
        )


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    rep_path = root / "reputation_timeseries.jsonl"
    state_path = root / "agent_state_snapshots.jsonl"
    checkpoint: Dict[str, str] = {}
    timeseries: List[Dict[str, Any]] = []
    snapshots: List[Dict[str, Any]] = []
    agent_state: Dict[str, Dict[str, Any]] = {}
    past_checkpoint: Dict[str, bool] = {}
    loaded = False

    if not rebuild:
        loaded_data = _load_state(root)
        if loaded_data is not None:
            timeseries, snapshots, agent_state, checkpoint = loaded_data
            timeseries = list(timeseries)
            snapshots = list(snapshots)
            agent_state = {k: dict(v) for k, v in agent_state.items()}
            checkpoint = dict(checkpoint)
            loaded = True

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        eid = ev.get("event_id", "")
        if loaded and scope_key in checkpoint:
            if not past_checkpoint.get(scope_key):
                if eid == checkpoint[scope_key]:
                    past_checkpoint[scope_key] = True
                continue
        checkpoint[scope_key] = eid
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        agent_id = actor.get("agent_id", "")
        if not agent_id:
            continue
        if agent_id not in agent_state:
            agent_state[agent_id] = {"agency_budget": 0.0, "trust_band": 0, "escrow_locked": 0.0, "incident_points": 0.0}
        if action == "EVALUATION_RECORDED":
            inc = payload.get("incident", {})
            if inc.get("raised"):
                agent_state[agent_id]["incident_points"] = agent_state[agent_id].get("incident_points", 0) + 1
            timeseries.append({
                "ts": ts, "agent_id": agent_id, "event": "evaluation",
                "score": payload.get("score"), "incident": inc,
            })
        elif action in ("ESCROW_LOCKED", "ESCROW_RELEASED", "ESCROW_SLASHED"):
            amt = float(payload.get("amount", 0) or 0)
            if action == "ESCROW_LOCKED":
                agent_state[agent_id]["escrow_locked"] = agent_state[agent_id].get("escrow_locked", 0) + amt
            elif action == "ESCROW_RELEASED":
                agent_state[agent_id]["escrow_locked"] = max(0, agent_state[agent_id].get("escrow_locked", 0) - amt)
            elif action == "ESCROW_SLASHED":
                agent_state[agent_id]["escrow_locked"] = max(0, agent_state[agent_id].get("escrow_locked", 0) - amt)
                agent_state[agent_id]["incident_points"] = agent_state[agent_id].get("incident_points", 0) + 1
            timeseries.append({"ts": ts, "agent_id": agent_id, "event": action.lower(), "amount": amt})
        elif action == "TRUST_BAND_CHANGED":
            band = int(payload.get("band", 0) or 0)
            agent_state[agent_id]["trust_band"] = band
            timeseries.append({"ts": ts, "agent_id": agent_id, "event": "trust_band_changed", "band": band})
        elif action == "BUDGET_ADJUSTED":
            delta = float(payload.get("delta", 0) or 0)
            agent_state[agent_id]["agency_budget"] = agent_state[agent_id].get("agency_budget", 0) + delta
            timeseries.append({"ts": ts, "agent_id": agent_id, "event": "budget_adjusted", "delta": delta})
        snapshots.append({"ts": ts, "agent_id": agent_id, **agent_state[agent_id].copy()})

    with open(rep_path, "w", encoding="utf-8") as f:
        for r in timeseries:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(state_path, "w", encoding="utf-8") as f:
        for r in snapshots[-1000:]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "reputation", checkpoint)
    _save_state(root, timeseries, snapshots, agent_state, checkpoint)
