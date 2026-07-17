"""Ch4 Product API: safe summaries for workflows, runs, approvals, incidents, policies, metrics."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from hg_gateway.shared_storage import list_agent_decisions, list_overseer_timeseries

from hg_gateway.approval_summary import normalize_runtime_approval

from ..core.config import settings
from .run_index_db import list_runs as _list_runs, get_run as _get_run
try:
    from hg_core.task_graph.planner import PlannerConstraints
    from hg_core.task_graph.planner_templates import TEMPLATES
except Exception:  # pragma: no cover
    PlannerConstraints = None
    TEMPLATES = {}


def _product_tenant_id() -> str:
    return (os.getenv("HG_PRODUCT_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


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


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _sanitize_summary_blob(value: Any) -> Any:
    blocked_exact = {"internal_path", "secret", "api_key", "token", "password", "credentials", "raw_prompt"}
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_s = str(key)
            if key_s.lower() in blocked_exact:
                continue
            out[key_s] = _sanitize_summary_blob(item)
        return out
    if isinstance(value, list):
        return [_sanitize_summary_blob(x) for x in value[:100]]
    if isinstance(value, str) and len(value) > 2000:
        return value[:2000]
    return value


def _runtime_approval_store():
    from hg_gateway.store import get_store

    return get_store()


def _resolve_flat_run_record(run_id: str) -> tuple[Path | None, dict[str, Any]]:
    root = _workspace_root()
    if not root:
        return None, {}
    path = root / "memory" / "automation" / "dag_runs" / f"{run_id}.json"
    return path, _json_dict(path)


def _build_timeline_from_node_states(node_states: Any) -> list[dict[str, Any]]:
    if not isinstance(node_states, dict):
        return []
    rows: list[dict[str, Any]] = []
    for node_id, node_blob in node_states.items():
        if not isinstance(node_blob, dict):
            continue
        rows.append(
            {
                "node_id": str(node_blob.get("id") or node_id),
                "node_type": node_blob.get("type"),
                "assigned_entity": node_blob.get("assigned_entity"),
                "status": node_blob.get("status"),
                "attempt_count": node_blob.get("attempt_count"),
                "started_at": node_blob.get("started_at"),
                "ended_at": node_blob.get("ended_at"),
                "duration_ms": node_blob.get("duration_ms"),
                "error": _sanitize_summary_blob(node_blob.get("error")),
            }
        )
    rows.sort(key=lambda row: _as_epoch(row.get("started_at")), reverse=False)
    return rows


def _audit_summary_from_run_record(run_record: dict[str, Any]) -> dict[str, Any]:
    node_states = run_record.get("node_states")
    node_outputs = run_record.get("node_outputs")
    node_count = len(node_states) if isinstance(node_states, dict) else 0
    completed_nodes = 0
    if isinstance(node_states, dict):
        for node_blob in node_states.values():
            if isinstance(node_blob, dict) and str(node_blob.get("status") or "").lower() in {"done", "completed"}:
                completed_nodes += 1

    execution = {}
    read_content = {}
    if isinstance(node_outputs, dict):
        execute_blob = node_outputs.get("execute_task")
        read_blob = node_outputs.get("read_content_queue")
        if isinstance(execute_blob, dict):
            execution = _sanitize_summary_blob(execute_blob.get("result") or execute_blob)
        if isinstance(read_blob, dict):
            read_content = _sanitize_summary_blob(read_blob.get("result") or read_blob)

    return _sanitize_summary_blob(
        {
            "final_status": run_record.get("final_status") or run_record.get("status"),
            "node_count": node_count,
            "completed_nodes": completed_nodes,
            "budget_used": ((run_record.get("state") or {}).get("budget_used") if isinstance(run_record.get("state"), dict) else {}),
            "execution": execution,
            "read_content": read_content,
        }
    )


# ----- Workflows -----


def list_workflows(status: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    """List workflows (from dag registry); safe summary only."""
    root = _workspace_root()
    items: list[dict] = []
    total = 0
    if root:
        reg_path = root / "memory" / "automation" / "dag_registry.json"
        if reg_path.exists():
            try:
                data = json.loads(reg_path.read_text(encoding="utf-8"))
                for wf_id in data:
                    items.append({
                        "id": wf_id,
                        "name": wf_id,
                        "status": "active",
                        "readiness": "supervised",
                    })
                total = len(items)
            except (json.JSONDecodeError, OSError):
                pass
    if status:
        items = [i for i in items if i.get("status") == status]
        total = len(items)
    items = items[offset : offset + limit]
    return {"items": items, "total": total}


def get_workflow(wf_id: str) -> dict | None:
    """Get workflow detail (safe summary)."""
    root = _workspace_root()
    if not root:
        return None
    reg_path = root / "memory" / "automation" / "dag_registry.json"
    if not reg_path.exists():
        return None
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        if wf_id not in data:
            return None
        return {
            "id": wf_id,
            "name": wf_id,
            "status": "active",
            "readiness": "supervised",
            "purpose": "",
            "recent_runs": [],
        }
    except (json.JSONDecodeError, OSError):
        return None


def list_workflow_runs(wf_id: str, limit: int = 50, offset: int = 0) -> dict:
    """List runs for a workflow (graph_id match)."""
    rows = _list_runs(limit=offset + limit)
    matching = [r for r in rows if r.get("graph_id") == wf_id]
    total = len(matching)
    page = matching[offset:offset + limit]
    items = [
        {"run_id": r["run_id"], "graph_id": r["graph_id"], "status": r["status"], "started_at": r.get("started_at"), "ended_at": r.get("ended_at")}
        for r in page
    ]
    return {"items": items, "total": total}


# ----- Runs (safe summary) -----


def list_runs(workflow_id: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    """List runs; optional filter by workflow_id, status."""
    rows = _list_runs(limit=1000)
    if workflow_id:
        rows = [r for r in rows if r.get("graph_id") == workflow_id]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    total = len(rows)
    page = rows[offset:offset + limit]
    items = [
        {"run_id": r["run_id"], "graph_id": r["graph_id"], "status": r["status"], "started_at": r.get("started_at"), "ended_at": r.get("ended_at")}
        for r in page
    ]
    return {"items": items, "total": total}


def get_run(run_id: str) -> dict | None:
    """Get run detail: safe summary only (no internal paths, no raw prompts)."""
    r = _get_run(run_id)
    if not r:
        return None
    out: dict[str, Any] = {
        "run_id": r["run_id"],
        "graph_id": r["graph_id"],
        "status": r["status"],
        "started_at": r.get("started_at"),
        "ended_at": r.get("ended_at"),
        "audit_summary": {},
        "trace_timeline": [],
    }
    run_dir = r.get("run_dir")
    if run_dir:
        rd = Path(run_dir)
        summary_path = rd / "summary.json"
        state_path = rd / "state.json"
        if _path_exists(summary_path):
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                out["audit_summary"] = _sanitize_summary_blob(summary or {})
            except (json.JSONDecodeError, OSError):
                pass
        if not out["trace_timeline"] and _path_exists(state_path):
            state = _json_dict(state_path)
            out["trace_timeline"] = _build_timeline_from_node_states(state.get("node_states") if isinstance(state, dict) else None)

    if not out["audit_summary"] or not out["trace_timeline"]:
        _, flat_run = _resolve_flat_run_record(run_id)
        if flat_run:
            if not out["audit_summary"]:
                out["audit_summary"] = _audit_summary_from_run_record(flat_run)
            if not out["trace_timeline"]:
                out["trace_timeline"] = _build_timeline_from_node_states(flat_run.get("node_states"))
    return out


def list_run_artifacts(run_id: str) -> dict | None:
    """List run artifacts metadata only (no content)."""
    r = _get_run(run_id)
    if not r:
        return None
    rd = Path(r["run_dir"])
    if not _path_exists(rd):
        run_record_path, flat_run = _resolve_flat_run_record(run_id)
        if not flat_run:
            return {"items": []}
        items: list[dict[str, Any]] = []
        if run_record_path and run_record_path.exists():
            items.append({"name": run_record_path.name, "kind": "file", "size": run_record_path.stat().st_size})
        node_outputs = flat_run.get("node_outputs")
        if isinstance(node_outputs, dict):
            execute_blob = node_outputs.get("execute_task")
            if isinstance(execute_blob, dict):
                result_blob = execute_blob.get("result")
                result_blob = result_blob if isinstance(result_blob, dict) else execute_blob
                draft_path = str(result_blob.get("draft_artifact") or "").strip()
                if draft_path:
                    dp = Path(draft_path)
                    if dp.exists():
                        root = _workspace_root()
                        name = dp.name
                        if root:
                            try:
                                name = str(dp.resolve().relative_to(root.resolve()))
                            except Exception:
                                name = dp.name
                        items.append({"name": name, "kind": "file", "size": dp.stat().st_size})
        return {"items": items}
    items = []
    try:
        for p in rd.rglob("*"):
            try:
                if p.is_file():
                    rel = str(p.relative_to(rd))
                    items.append({"name": rel, "kind": "file", "size": p.stat().st_size})
            except OSError:
                continue
    except OSError:
        return {"items": []}
    return {"items": items}


# ----- Approvals -----


def _iter_decision_entries() -> Iterable[dict[str, Any]]:
    root = _workspace_root()
    if not root:
        return
    base = root / "memory" / "automation"
    for agent_dir in base.iterdir():
        if not agent_dir.is_dir():
            continue
        workflow = agent_dir.name.replace("automation-", "")
        shared_entries = list_agent_decisions(workflow, limit=500)
        if not shared_entries:
            continue
        entries = list(reversed(shared_entries))
        for entry in entries:
            yield {
                "id": entry.get("decision_id") or entry.get("id") or "",
                "timestamp": entry.get("timestamp"),
                "workflow": workflow,
                "decision": entry.get("decision") or entry.get("action") or "approved",
                "action": entry.get("action"),
                "rationale": entry.get("rationale"),
                "alternatives": entry.get("alternatives"),
            }


def list_approvals(limit: int = 50, offset: int = 0, status: str | None = None) -> dict:
    """List approvals from the gateway runtime store, falling back only if store access fails."""
    try:
        status_filter = (status or "all").strip().lower()
        approvals = _runtime_approval_store().approval_list(_product_tenant_id(), status_filter=status_filter)
        approvals = [_sanitize_summary_blob(normalize_runtime_approval(item)) for item in approvals]
        approvals.sort(key=lambda row: _as_epoch(row.get("createdAt") or row.get("timestamp")), reverse=True)
        total = len(approvals)
        items = approvals[offset : offset + limit]
        return {"items": items, "total": total}
    except Exception:
        all_entries = list(_iter_decision_entries())
        total = len(all_entries)
        items = all_entries[offset : offset + limit]
        return {"items": items, "total": total}


def get_approval(aid: str) -> dict | None:
    """Get single approval decision by id from runtime store, falling back only if store access fails."""
    try:
        entry = _runtime_approval_store().approval_get(_product_tenant_id(), aid)
        if entry:
            return _sanitize_summary_blob(normalize_runtime_approval(entry))
    except Exception:
        pass
    for entry in _iter_decision_entries():
        if entry.get("id") == aid:
            return entry
    return None


# ----- Deadletters -----


def _list_deadletter_from_dag_runs() -> Iterable[dict[str, Any]]:
    root = _workspace_root()
    if not root:
        return
    dag_runs = root / "memory" / "automation" / "dag_runs"
    if not dag_runs.exists():
        return
    for summary_path in dag_runs.rglob("summary.json"):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        status = (summary.get("final_status") or summary.get("status") or "").lower()
        if status in {"completed", "success"}:
            continue
        run_id = summary.get("run_id") or summary_path.parent.name
        yield {
            "id": run_id,
            "graph_id": summary.get("graph_id"),
            "status": summary.get("final_status") or summary.get("status"),
            "started_at": summary.get("started_at"),
            "ended_at": summary.get("ended_at") or summary.get("updated_at"),
            "error": summary.get("error_summary") or summary.get("failure_class"),
            "run_dir": str(summary_path.parent),
        }


def list_deadletters(limit: int = 50, offset: int = 0) -> dict:
    """List dead-letter items based on DAG run outcomes."""
    entries = list(_list_deadletter_from_dag_runs())
    entries.sort(key=lambda row: _as_epoch(row.get("started_at")), reverse=True)
    total = len(entries)
    page = entries[offset : offset + limit]
    return {"items": page, "total": total}


def get_deadletter(did: str) -> dict | None:
    """Fetch a single dead-letter/terminal failure by run_id."""
    for entry in _list_deadletter_from_dag_runs():
        if entry.get("id") == did:
            return entry
    return None


def resolve_run_artifact_path(run_id: str, name: str) -> Path | None:
    """Resolve a run artifact path for download; name is relative to run_dir."""
    r = _get_run(run_id)
    if not r:
        return None
    run_dir = r.get("run_dir")
    if not run_dir:
        return None
    rd = Path(str(run_dir))
    if not _path_exists(rd):
        return None
    candidate = (rd / name).resolve()
    try:
        rd_resolved = rd.resolve()
        if not str(candidate).startswith(str(rd_resolved)):
            return None
    except OSError:
        return None
    if candidate.is_file():
        return candidate
    return None


# ----- Policies -----


def get_blacklist() -> dict:
    """Get blacklist policy (safe summary)."""
    root = _workspace_root()
    if root:
        p = root / "memory" / "overseer" / "blacklist.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return {"categories": [], "rules": []}


# ----- Metrics -----


def get_metrics_summary(period: str = "daily") -> dict:
    """Metrics summary (daily/weekly); safe summary."""
    root = _workspace_root()
    cost = {}
    sla = {}
    pdf_dashboard = {}
    period_hours = 24 if period == "daily" else 24 * 7
    try:
        from .activity_service import get_dashboard_data

        dash = get_dashboard_data(hours=period_hours)
        if isinstance(dash, dict):
            pdf_dashboard = dash.get("pdf_dashboard") or {}
    except Exception:
        pdf_dashboard = {}
    if root:
        rows = list_overseer_timeseries(hours=period_hours, limit=100000)
        if rows:
            count = len(rows)
            cost = {"runs_24h": count}
            sla = {"success_ratio": 1.0}
    return {"period": period, "cost": cost, "sla": sla, "pdf_dashboard": pdf_dashboard}


def get_metrics_reports(limit: int = 20) -> dict:
    try:
        from .activity_service import get_dashboard_reports

        return get_dashboard_reports(limit=max(1, min(limit, 100)))
    except Exception:
        return {"latest_pdf": None, "latest_png": None, "items": []}


# ----- Templates -----


def list_templates() -> dict:
    items: list[dict] = []
    for name, fn in TEMPLATES.items():
        doc = (fn.__doc__ or "").strip()
        try:
            dag = instantiate_template(name, {})
            graph_id = dag.get("dag", {}).get("graph_id")
            node_count = len(dag.get("dag", {}).get("nodes", []))
        except Exception:
            graph_id = None
            node_count = None
        items.append({
            "template_id": name,
            "description": doc.splitlines()[0] if doc else None,
            "graph_id": graph_id,
            "node_count": node_count,
        })
    return {"items": items, "total": len(items)}


def instantiate_template(template_id: str, payload: dict) -> dict:
    if template_id not in TEMPLATES:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "template not found"}}
    if PlannerConstraints is None:
        return {"ok": False, "error": {"code": "TEMPLATE_UNAVAILABLE", "message": "planner unavailable"}}
    goal = payload.get("goal") or f"Template: {template_id}"
    context = payload.get("context") or {}
    constraints = PlannerConstraints()
    dag = TEMPLATES[template_id](goal=goal, context=context, constraints=constraints)
    return {"ok": True, "template_id": template_id, "dag": dag}


# ----- Audit export -----


def get_audit_report(run_id: str) -> dict | None:
    r = get_run(run_id)
    if not r:
        return None
    return {
        "run_id": r.get("run_id"),
        "graph_id": r.get("graph_id"),
        "status": r.get("status"),
        "started_at": r.get("started_at"),
        "ended_at": r.get("ended_at"),
        "audit_summary": r.get("audit_summary") or {},
    }
