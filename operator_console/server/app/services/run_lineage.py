"""Run lineage summary helpers for workflow, swarm, and chat navigation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_gateway.events_ledger import list_events

from .run_index_db import get_run as _get_run, list_runs as _list_runs
from .swarm_tree import get_swarm_tree


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _as_epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            pass
        try:
            normalized = text.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(timezone.utc).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _json_dict(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _row_href(run_id: str | None) -> str | None:
    rid = str(run_id or "").strip()
    return f"#/runs/{rid}" if rid else None


def _workflow_href(workflow_id: str | None) -> str | None:
    wid = str(workflow_id or "").strip()
    return f"#/activity?workflow_id={wid}" if wid else None


def _parse_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    try:
        raw = row.get("payload_json")
        if isinstance(raw, str) and raw.strip():
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                payload = loaded
    except Exception:
        payload = {}
    return payload


def _related_ids_from_events(run_id: str) -> dict[str, list[str]]:
    tenant_id = ((os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default")
    try:
        rows = list_events(tenant_id, run_id=run_id, limit=200)
    except Exception:
        return {"chat_ids": [], "workflow_ids": [], "swarm_run_ids": []}
    chat_ids: list[str] = []
    workflow_ids: list[str] = []
    swarm_run_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload = _parse_payload(row)
        for candidate in (
            row.get("chat_id"),
            payload.get("chat_id"),
            payload.get("reply_chat_id"),
        ):
            text = str(candidate or "").strip()
            if text and text not in chat_ids:
                chat_ids.append(text)
        for candidate in (
            row.get("workflow_id"),
            row.get("graph_id"),
            payload.get("workflow_id"),
            payload.get("graph_id"),
        ):
            text = str(candidate or "").strip()
            if text and text not in workflow_ids:
                workflow_ids.append(text)
        for candidate in (
            row.get("swarm_run_id"),
            payload.get("swarm_run_id"),
            payload.get("parent_swarm_run_id"),
        ):
            text = str(candidate or "").strip()
            if text and text not in swarm_run_ids:
                swarm_run_ids.append(text)
    return {
        "chat_ids": chat_ids[:10],
        "workflow_ids": workflow_ids[:10],
        "swarm_run_ids": swarm_run_ids[:10],
    }


def _summarize_run_row(row: dict[str, Any] | None, run_id: str) -> dict[str, Any]:
    data = dict(row or {})
    rid = str(data.get("run_id") or run_id).strip() or run_id
    return {
        "run_id": rid,
        "graph_id": str(data.get("graph_id") or "").strip() or None,
        "status": str(data.get("status") or "").strip() or None,
        "started_at": data.get("started_at"),
        "ended_at": data.get("ended_at"),
        "correlation_id": str(data.get("correlation_id") or "").strip() or None,
        "run_href": _row_href(rid),
    }


def _build_lineage_graph(run_id: str, parent_chain: list[dict[str, Any]], child_runs: list[dict[str, Any]], workflow_id: str | None) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_node(node_id: str, *, kind: str, label: str | None = None) -> None:
        nid = str(node_id or "").strip()
        if not nid or nid in seen:
            return
        seen.add(nid)
        nodes.append({"id": nid, "kind": kind, "label": label or nid})

    previous = None
    for ancestor in parent_chain:
        ancestor_id = str(ancestor.get("run_id") or "").strip()
        if not ancestor_id:
            continue
        add_node(ancestor_id, kind="parent")
        if previous:
            edges.append({"from": ancestor_id, "to": previous, "kind": "swarm_parent"})
        previous = ancestor_id

    add_node(run_id, kind="current")
    if previous:
        edges.append({"from": previous, "to": run_id, "kind": "swarm_parent"})

    for child in child_runs:
        child_id = str(child.get("run_id") or "").strip()
        if not child_id:
            continue
        add_node(child_id, kind="child")
        edges.append({"from": run_id, "to": child_id, "kind": "swarm_child"})

    if workflow_id:
        workflow_node = f"workflow_{''.join(ch if ch.isalnum() else '_' for ch in workflow_id)}"
        add_node(workflow_node, kind="workflow", label=workflow_id)
        edges.append({"from": workflow_node, "to": run_id, "kind": "workflow"})

    return {"nodes": nodes, "edges": edges}


def build_run_lineage_summary(run_id: str, *, run_record: dict[str, Any] | None = None) -> dict[str, Any]:
    run = dict(run_record or {})
    if not run:
        fetched = _get_run(run_id)
        if fetched:
            run = dict(fetched)

    if not run:
        return {
            "run_id": run_id,
            "status": "missing",
            "graph_id": None,
            "workflow_id": None,
            "run_href": _row_href(run_id),
            "workflow_href": None,
            "activity_href": None,
            "parent_run_id": None,
            "child_run_ids": [],
            "parent_chain": [],
            "child_runs": [],
            "related_chat_ids": [],
            "related_workflow_ids": [],
            "related_swarm_run_ids": [],
            "swarm_tree": {"run_id": run_id, "child_run_ids": [], "parent_run_id": None},
            "lineage_graph": {"nodes": [], "edges": []},
        }

    workflow_id = str(run.get("graph_id") or "").strip() or None
    correlation_id = str(run.get("correlation_id") or "").strip() or None
    swarm_tree = get_swarm_tree(run_id)
    parent_run_id = str(swarm_tree.get("parent_run_id") or "").strip() or None
    child_run_ids = [str(rid).strip() for rid in (swarm_tree.get("child_run_ids") or []) if str(rid).strip()]

    correlated_runs: list[dict[str, Any]] = []
    if correlation_id:
        try:
            rows = _list_runs(limit=1000)
        except Exception:
            rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("correlation_id") or "").strip() != correlation_id:
                continue
            rid = str(row.get("run_id") or "").strip()
            if not rid or rid == run_id:
                continue
            correlated_runs.append(_summarize_run_row(row, rid))
        correlated_runs.sort(key=lambda item: _as_epoch(item.get("started_at")), reverse=False)

    current_started_at = _as_epoch(run.get("started_at"))
    if not parent_run_id and correlated_runs:
        earlier = [row for row in correlated_runs if _as_epoch(row.get("started_at")) and _as_epoch(row.get("started_at")) < current_started_at]
        if earlier:
            parent_run_id = earlier[0]["run_id"]
    if not child_run_ids and correlated_runs:
        child_run_ids = [
            row["run_id"]
            for row in correlated_runs
            if row["run_id"] != parent_run_id and _as_epoch(row.get("started_at")) >= current_started_at
        ][:12]

    parent_chain: list[dict[str, Any]] = []
    seen: set[str] = {run_id}
    current_parent = parent_run_id
    depth = 0
    while current_parent and current_parent not in seen and depth < 10:
        seen.add(current_parent)
        parent_row = _get_run(current_parent)
        if not parent_row:
            break
        parent_summary = _summarize_run_row(parent_row, current_parent)
        parent_chain.insert(0, parent_summary)
        current_parent = str(get_swarm_tree(parent_summary["run_id"]).get("parent_run_id") or "").strip() or None
        depth += 1

    child_runs: list[dict[str, Any]] = []
    for child_id in child_run_ids[:12]:
        child_row = _get_run(child_id)
        child_runs.append(_summarize_run_row(child_row, child_id))

    related = _related_ids_from_events(run_id)
    summary = {
        "run_id": str(run.get("run_id") or run_id).strip() or run_id,
        "status": str(run.get("status") or "unknown").strip() or "unknown",
        "graph_id": workflow_id,
        "workflow_id": workflow_id,
        "correlation_id": correlation_id or None,
        "run_href": _row_href(run_id),
        "workflow_href": _workflow_href(workflow_id),
        "activity_href": f"#/activity?run_id={run_id}",
        "parent_run_id": parent_run_id,
        "child_run_ids": child_run_ids,
        "parent_chain": parent_chain,
        "child_runs": child_runs,
        "correlated_runs": correlated_runs,
        "related_chat_ids": related["chat_ids"],
        "related_workflow_ids": related["workflow_ids"],
        "related_swarm_run_ids": related["swarm_run_ids"],
        "swarm_tree": {
            "run_id": run_id,
            "child_run_ids": child_run_ids,
            "parent_run_id": parent_run_id,
        },
    }
    summary["lineage_graph"] = _build_lineage_graph(run_id, parent_chain, child_runs, workflow_id)
    summary["root_run_id"] = parent_chain[0]["run_id"] if parent_chain else run_id
    if related["chat_ids"]:
        summary["chat_activity_href"] = f"#/activity?chat_id={related['chat_ids'][0]}"
    else:
        summary["chat_activity_href"] = None
    return summary
