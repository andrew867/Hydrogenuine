"""
Viz Phase 2: DAG view — workflow/DAG runs and per-run graph (read-only).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.viz.schema import viz_node, viz_edge


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def adapt_dag_runs_list(
    workspace_root: Path,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return list of DAG runs: run_id, graph_id, status, started_at, run_dir."""
    root = Path(workspace_root)
    runs_dir = root / "memory" / "automation" / "dag_runs"
    if not runs_dir.is_dir():
        return []
    entries: List[Dict[str, Any]] = []
    for path in sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if len(entries) >= limit:
            break
        data = _load_json(path)
        run_id = data.get("run_id") or path.stem
        graph_id = data.get("graph_id") or (data.get("dag") or {}).get("graph_id") or ""
        entries.append({
            "run_id": run_id,
            "graph_id": graph_id,
            "status": data.get("final_status") or data.get("status") or "unknown",
            "started_at": data.get("started_at") or data.get("timestamp") or "",
            "run_dir": str(data.get("run_dir") or path.parent),
        })
    return entries


def adapt_dag_run_graph(
    workspace_root: Path,
    run_id: str,
) -> Dict[str, Any]:
    """
    Return unified viz graph for one DAG run: nodes (work items / steps), edges (delegation/handoff).
    Reads delegation_graph.json from run dir if present; else builds minimal nodes from state.json.
    """
    root = Path(workspace_root)
    runs_dir = root / "memory" / "automation" / "dag_runs"
    if not runs_dir.is_dir():
        return {"nodes": [], "edges": []}
    run_dir: Optional[Path] = None
    for path in runs_dir.glob("*.json"):
        data = _load_json(path)
        if str(data.get("run_id") or path.stem) != run_id:
            continue
        run_dir_str = data.get("run_dir")
        if run_dir_str:
            run_dir = root / run_dir_str if not Path(run_dir_str).is_absolute() else Path(run_dir_str)
        else:
            run_dir = path.parent if path.parent != runs_dir else runs_dir / run_id
        break
    if not run_dir:
        run_dir = runs_dir / run_id
    if not run_dir or not run_dir.exists():
        return {"nodes": [], "edges": []}
    dg_path = run_dir / "delegation_graph.json"
    state_path = run_dir / "state.json"
    nodes_out: List[Dict[str, Any]] = []
    edges_out: List[Dict[str, Any]] = []
    if dg_path.exists():
        dg = _load_json(dg_path)
        for n in dg.get("nodes") or []:
            nid = n.get("id") or ""
            if nid:
                nodes_out.append(viz_node(nid, "work_item", {"owner": n.get("owner"), "status": n.get("status")}, None))
        for e in dg.get("edges") or []:
            fr, to = e.get("from"), e.get("to")
            if fr and to:
                edges_out.append(viz_edge(fr, to, e.get("event_type") or "delegation", None))
    if not nodes_out and state_path.exists():
        state = _load_json(state_path)
        node_states = state.get("node_states") or state.get("state") or {}
        if isinstance(node_states, dict):
            for nid, ndata in node_states.items():
                nodes_out.append(viz_node(nid, "run_step", ndata if isinstance(ndata, dict) else {}, None))
    return {"nodes": nodes_out, "edges": edges_out}


def adapt_dag_view(
    workspace_root: Path,
    run_id: Optional[str] = None,
    runs_limit: int = 50,
) -> Dict[str, Any]:
    """
    Combined DAG view: runs list and optionally graph for one run.
    Returns { runs: [...], graph?: { nodes, edges } }.
    """
    root = Path(workspace_root)
    out: Dict[str, Any] = {"runs": adapt_dag_runs_list(root, limit=runs_limit)}
    if run_id:
        out["graph"] = adapt_dag_run_graph(root, run_id)
    return out
