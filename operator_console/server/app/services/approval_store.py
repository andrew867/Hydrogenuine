"""Approval and dedup query helpers for operator/workflow APIs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_gateway.shared_storage import list_agent_decisions


def _resolve_workspace_root(workspace_root: Optional[Path]) -> Optional[Path]:
    if workspace_root is not None:
        return Path(workspace_root)
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _json_dict(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


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


def _iter_decision_entries(root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    base = root / "memory" / "automation"
    if not base.exists():
        return out
    for agent_dir in base.iterdir():
        if not agent_dir.is_dir():
            continue
        workflow_id = agent_dir.name.replace("automation-", "")
        shared_decisions = list_agent_decisions(workflow_id, limit=1000)
        source = "gateway-db"
        for entry in shared_decisions:
            if not isinstance(entry, dict):
                continue
            out.append(
                {
                    "id": str(entry.get("decision_id") or entry.get("id") or ""),
                    "workflow_id": str(entry.get("workflow_id") or entry.get("task_id") or workflow_id),
                    "timestamp": entry.get("timestamp"),
                    "decision": str(entry.get("decision") or "approved"),
                    "action": entry.get("action"),
                    "rationale": entry.get("rationale"),
                    "alternatives": entry.get("alternatives") if isinstance(entry.get("alternatives"), list) else [],
                    "policy_version": entry.get("policy_version") or "default",
                    "source": source,
                }
            )
    out.sort(key=lambda item: _as_epoch(item.get("timestamp")), reverse=True)
    return out


def list_approvals(
    *,
    workspace_root: Optional[Path] = None,
    workflow_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    root = _resolve_workspace_root(workspace_root)
    if not root:
        return {"items": [], "total": 0}
    rows = _iter_decision_entries(root)
    if workflow_id:
        wf = str(workflow_id)
        rows = [row for row in rows if str(row.get("workflow_id")) == wf]
    total = len(rows)
    page = rows[offset : offset + max(1, limit)]
    return {"items": page, "total": total}


def _dedupe_entries_for_workflow(root: Path, workflow_id: str) -> List[Dict[str, Any]]:
    session_target = f"automation-{workflow_id}"
    path = root / "memory" / "automation" / session_target / "post_dedupe.json"
    payload = _json_dict(path)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return []
    rows: List[Dict[str, Any]] = []
    for idem_key, value in entries.items():
        if not isinstance(value, dict):
            continue
        rows.append(
            {
                "idempotency_key": str(idem_key),
                "timestamp": value.get("at"),
                "tool_name": value.get("tool_name"),
                "timeout_s": value.get("timeout_s"),
                "outputs": value.get("outputs") if isinstance(value.get("outputs"), dict) else {},
                "usage": value.get("usage") if isinstance(value.get("usage"), dict) else {},
            }
        )
    rows.sort(key=lambda item: _as_epoch(item.get("timestamp")), reverse=True)
    return rows


def _workflow_run_summary(root: Path, workflow_id: str) -> Dict[str, Any]:
    run_root = root / "memory" / "automation" / "dag_runs"
    if not run_root.exists():
        return {"run_count": 0, "latest_run_id": None, "latest_status": None}
    run_count = 0
    latest: Dict[str, Any] | None = None
    for summary_path in run_root.rglob("summary.json"):
        summary = _json_dict(summary_path)
        if str(summary.get("graph_id") or "") != workflow_id:
            continue
        run_count += 1
        started_at = summary.get("started_at")
        if latest is None or _as_epoch(started_at) > _as_epoch(latest.get("started_at")):
            latest = {
                "run_id": summary.get("run_id") or summary_path.parent.name,
                "status": summary.get("final_status") or summary.get("status"),
                "started_at": started_at,
            }
    if latest is None:
        return {"run_count": run_count, "latest_run_id": None, "latest_status": None}
    return {
        "run_count": run_count,
        "latest_run_id": latest.get("run_id"),
        "latest_status": latest.get("status"),
    }


def get_workflow_dedup(
    workflow_id: str,
    *,
    workspace_root: Optional[Path] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    root = _resolve_workspace_root(workspace_root)
    if not root:
        return {"workflow_id": workflow_id, "items": [], "total": 0, "run_summary": {"run_count": 0}}
    rows = _dedupe_entries_for_workflow(root, workflow_id)
    return {
        "workflow_id": workflow_id,
        "items": rows[: max(1, limit)],
        "total": len(rows),
        "run_summary": _workflow_run_summary(root, workflow_id),
    }
