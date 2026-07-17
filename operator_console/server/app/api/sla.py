"""SLA API: daily and weekly report generation."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import require_api_key

router = APIRouter()


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _gather_traces_from_workspace(root: Path | None, limit: int = 2000) -> list:
    """Build trace rows from indexed runs first, then fall back to workspace discovery."""
    if not root:
        return []
    try:
        from ..services.run_index_db import list_runs

        rows = list_runs(limit=limit)
        traces = []
        for row in rows:
            status_raw = str(row.get("status") or "").lower()
            trace_status = "success" if status_raw == "completed" else ("degraded" if status_raw == "degraded" else "failed")
            traces.append({
                "run_id": row.get("run_id"),
                "workflow_id": row.get("graph_id"),
                "status": trace_status,
                "failure_class": row.get("failure_class"),
                "budget_used": row.get("budget_used"),
            })
        if traces:
            return traces
    except Exception:
        pass
    try:
        from hg_core.task_graph.operator_ux import _discover_runs

        rows = _discover_runs(root, limit=limit)
        traces = []
        for row in rows:
            status_raw = str(row.get("status") or "").lower()
            trace_status = "success" if status_raw == "completed" else ("degraded" if status_raw == "degraded" else "failed")
            traces.append({
                "run_id": row.get("run_id"),
                "workflow_id": row.get("workflow_id"),
                "status": trace_status,
                "failure_class": row.get("failure_class"),
                "budget_used": row.get("budget_used"),
            })
        return traces
    except Exception:
        return []


@router.get("/daily")
def daily_report(traces: str | None = None, _=Depends(require_api_key)):
    """Daily report from traces (optional query param traces=JSON array). When omitted, gathers from workspace dag_runs."""
    try:
        from hg_core.task_graph.sla_reporting import generate_daily_report
        root = _workspace_root()
        trace_list = None
        if traces:
            try:
                trace_list = json.loads(traces)
            except json.JSONDecodeError:
                pass
        if trace_list is None:
            trace_list = _gather_traces_from_workspace(root)
        report = generate_daily_report(traces=trace_list, workspace_root=root)
        return {"ok": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/weekly")
def weekly_report(traces: str | None = None, _=Depends(require_api_key)):
    """Weekly report from traces (optional query param traces=JSON array). When omitted, gathers from workspace dag_runs."""
    try:
        from hg_core.task_graph.sla_reporting import generate_weekly_report
        root = _workspace_root()
        trace_list = None
        if traces:
            try:
                trace_list = json.loads(traces)
            except json.JSONDecodeError:
                pass
        if trace_list is None:
            trace_list = _gather_traces_from_workspace(root)
        report = generate_weekly_report(traces=trace_list, workspace_root=root)
        return {"ok": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
