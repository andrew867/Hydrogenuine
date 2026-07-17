"""
Co-access molecules materializer: from READ + RETRIEVAL_SET events build molecules and edges.
Output: molecules.jsonl, molecules_edges.jsonl. Supports incremental (rebuild=False) using state file + checkpoint.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, load_checkpoint, save_checkpoint

STATE_KEY_SEP = "|"


def _state_path(root: Path) -> Path:
    return root / "molecules_state.json"


def _serialize_key(st: str, sid: str, agent_id: str) -> str:
    return f"{st}{STATE_KEY_SEP}{sid}{STATE_KEY_SEP}{agent_id}"


def _deserialize_key(s: str) -> Tuple[str, str, str]:
    parts = s.split(STATE_KEY_SEP, 2)
    return (parts[0], parts[1], parts[2] if len(parts) > 2 else "")


def _load_state(root: Path) -> Optional[Tuple[Dict[tuple, List[Dict[str, Any]]], Dict[str, str]]]:
    path = _state_path(root)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    raw = data.get("by_scope_agent")
    if not isinstance(raw, dict):
        return None
    by_scope_agent: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for k, items in raw.items():
        if isinstance(items, list):
            by_scope_agent[_deserialize_key(k)] = list(items)
    checkpoint = data.get("checkpoint")
    if not isinstance(checkpoint, dict):
        return None
    return (dict(by_scope_agent), checkpoint)


def _save_state(root: Path, by_scope_agent: Dict[tuple, List[Dict[str, Any]]], checkpoint: Dict[str, str]) -> None:
    raw = {_serialize_key(st, sid, aid): items for (st, sid, aid), items in by_scope_agent.items()}
    path = _state_path(root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"by_scope_agent": raw, "checkpoint": checkpoint}, f, ensure_ascii=False)


def _process_event(
    ev: Dict[str, Any],
    scope_type: str,
    scope_id: str,
    by_scope_agent: Dict[tuple, List[Dict[str, Any]]],
) -> None:
    action = ev.get("action")
    if action not in ("READ", "RETRIEVAL_SET"):
        return
    actor = ev.get("actor") or {}
    agent_id = actor.get("agent_id", "")
    obj = ev.get("object") or {}
    payload = ev.get("payload") or {}
    ts = ev.get("ts", "")
    if action == "READ":
        entity_id = obj.get("id", "")
        if entity_id:
            by_scope_agent[(scope_type, scope_id, agent_id)].append({
                "id": entity_id, "ts": ts, "action": "READ", "path": obj.get("path"),
            })
    elif action == "RETRIEVAL_SET":
        for eid_ref in payload.get("top_k_ids", []) or payload.get("selected_ids", []):
            if eid_ref:
                by_scope_agent[(scope_type, scope_id, agent_id)].append({
                    "id": eid_ref, "ts": ts, "action": "RETRIEVAL_SET",
                })


def _write_outputs(
    root: Path,
    by_scope_agent: Dict[tuple, List[Dict[str, Any]]],
    molecules_path: Path,
    edges_path: Path,
) -> None:
    with open(molecules_path, "w", encoding="utf-8") as f:
        for (st, sid, agent_id), items in sorted(by_scope_agent.items()):
            ids_seen = []
            for it in items:
                if it["id"] not in ids_seen:
                    ids_seen.append(it["id"])
            rec = {
                "scope_type": st, "scope_id": sid, "agent_id": agent_id,
                "selected_ids": ids_seen[-50:],
                "count": len(items),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    edge_counts: Dict[tuple, int] = defaultdict(int)
    for (st, sid, agent_id), items in by_scope_agent.items():
        ids_in_order = [it["id"] for it in items]
        for i, a in enumerate(ids_in_order):
            for b in ids_in_order[i + 1 : i + 21]:
                if a != b:
                    edge_counts[(st, sid, agent_id, tuple(sorted([a, b])))] += 1
    with open(edges_path, "w", encoding="utf-8") as f:
        for (st, sid, agent_id, pair), count in sorted(edge_counts.items(), key=lambda x: -x[1])[:5000]:
            f.write(json.dumps({
                "scope_type": st, "scope_id": sid, "agent_id": agent_id,
                "a": pair[0], "b": pair[1], "weight": count,
            }, ensure_ascii=False) + "\n")


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    molecules_path = root / "molecules.jsonl"
    edges_path = root / "molecules_edges.jsonl"
    checkpoint: Dict[str, str] = {}
    by_scope_agent: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    past_checkpoint: Dict[str, bool] = {}
    loaded = False

    if not rebuild:
        loaded_data = _load_state(root)
        if loaded_data is not None:
            by_scope_agent, prev_ck = loaded_data
            by_scope_agent = defaultdict(list, by_scope_agent)
            checkpoint = dict(prev_ck)
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
        _process_event(ev, scope_type, scope_id, by_scope_agent)

    _write_outputs(root, by_scope_agent, molecules_path, edges_path)
    save_checkpoint(workspace_root, "molecules", checkpoint)
    _save_state(root, dict(by_scope_agent), checkpoint)
