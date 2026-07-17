"""
Viz Phase 5: System-of-systems and dashboards — data map, operator widgets, deep-linking (read-only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from hg_core.ledger.ledger_writer import get_ledger_root, _iter_scope_paths
from hg_core.materializers._checkpoint import get_materialized_root
from hg_core.dashboards.reports import get_dashboard_for_role

# Known materialized tables for data map
MATERIALIZED_TABLES = (
    "decisions.jsonl",
    "work_items.jsonl",
    "incidents.jsonl",
    "handoffs.jsonl",
    "audit_events.jsonl",
    "policy_events.jsonl",
    "drift_scores.jsonl",
    "goal_integrity_scores.jsonl",
    "group_drift_scores.jsonl",
    "operator_guardrails.jsonl",
)


def adapt_data_map(workspace_root: Path) -> Dict[str, Any]:
    """
    Return data map: ledger scopes, materialized tables, DAG runs — for system-of-systems view.
    Each source has id, type, and link_params for deep-linking.
    """
    root = Path(workspace_root)
    sources: List[Dict[str, Any]] = []

    # Ledger scopes
    try:
        for scope_type, scope_id, _path in _iter_scope_paths(root):
            sources.append({
                "id": f"ledger:{scope_type}:{scope_id}",
                "type": "ledger_scope",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "link_params": {"view": "ledger_stream", "scope_type": scope_type, "scope_id": scope_id},
            })
    except Exception:
        pass

    # Materialized tables
    mat_root = get_materialized_root(root)
    added_tables: Set[str] = set()
    if mat_root.exists():
        for table in MATERIALIZED_TABLES:
            path = mat_root / table
            if path.exists():
                name = path.stem
                added_tables.add(name)
                sources.append({
                    "id": f"materialized:{name}",
                    "type": "materialized",
                    "name": name,
                    "link_params": {"view": "materialized", "table": name},
                })
        for path in mat_root.glob("*.jsonl"):
            if path.stem not in added_tables:
                added_tables.add(path.stem)
                sources.append({
                    "id": f"materialized:{path.stem}",
                    "type": "materialized",
                    "name": path.stem,
                    "link_params": {"view": "materialized", "table": path.stem},
                })

    # DAG runs
    dag_runs = root / "memory" / "automation" / "dag_runs"
    if dag_runs.exists():
        sources.append({
            "id": "automation:dag_runs",
            "type": "dag_runs",
            "link_params": {"view": "dag"},
        })

    return {"sources": sources}


def adapt_operator_widgets(
    workspace_root: Path,
    role: str = "operator",
    investor_mode: bool = False,
) -> Dict[str, Any]:
    """
    Return operator (or role) dashboard payload: widgets, role, evidence_links, etc.
    Read-only; delegates to get_dashboard_for_role.
    """
    root = Path(workspace_root)
    dashboard = get_dashboard_for_role(root, role, investor_mode=investor_mode)
    # Add deep_link hints to widgets for client routing
    for w in dashboard.get("widgets") or []:
        wid = w.get("id", "")
        if wid == "recent_decisions":
            w["link_params"] = {"view": "decisions"}
        elif wid == "recent_incidents":
            w["link_params"] = {"view": "incidents"}
        elif wid == "work_queue":
            w["link_params"] = {"view": "work_items"}
        elif wid == "summary":
            w["link_params"] = {"view": "summary"}
    return dashboard


def adapt_deep_link(
    workspace_root: Path,
    target_type: str,
    target_id: str,
) -> Dict[str, Any]:
    """
    Return deep-link descriptor for a target: view, params, optional fragment.
    target_type: decision | incident | work_item | run | node | evidence.
    """
    _root = Path(workspace_root)
    target_type = (target_type or "").strip().lower()
    target_id = (target_id or "").strip()
    view = "summary"
    params: Dict[str, str] = {}
    fragment: Optional[str] = None

    if target_type == "decision":
        view = "decision_explainer"
        params = {"decision_id": target_id}
        fragment = "proof-path"
    elif target_type == "incident":
        view = "incident"
        params = {"incident_id": target_id}
    elif target_type == "work_item":
        view = "work_item"
        params = {"work_item_id": target_id}
    elif target_type == "run":
        view = "dag"
        params = {"run_id": target_id}
    elif target_type == "node":
        view = "graph"
        params = {"node_id": target_id}
    elif target_type == "evidence":
        view = "evidence"
        params = {"event_id": target_id}
    else:
        params = {"target_type": target_type, "target_id": target_id}

    out: Dict[str, Any] = {"view": view, "params": params}
    if fragment:
        out["fragment"] = fragment
    return out
