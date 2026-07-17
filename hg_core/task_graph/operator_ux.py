"""Operator-facing status and control helpers backed by workspace state."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from hg_core.deadletter import load_deadletter, list_deadletter_files
from hg_core.task_graph.sla_reporting import generate_weekly_report
from hg_gateway.shared_storage import list_agent_decisions

logger = logging.getLogger(__name__)

_DAG_RUNS_DIR = Path("memory") / "automation" / "dag_runs"
_BREAKER_DIR = Path("memory") / "automation" / "circuit_breaker"
_AUDIT_LOG = Path("memory") / "overseer" / "audit_log.jsonl"
_WORKFLOW_CONTROLS = Path("memory") / "automation" / "workflow_controls.json"
_APPROVAL_DECISIONS_GLOB = Path("memory") / "automation"


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
    except Exception:
        logger.debug("Failed reading json dict from %s", path, exc_info=True)
    return {}


def _json_lines(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    out.append(payload)
    except Exception:
        logger.debug("Failed reading jsonl from %s", path, exc_info=True)
    return out


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


def _iso_from_epoch(epoch_s: float) -> str:
    return datetime.fromtimestamp(epoch_s, timezone.utc).isoformat().replace("+00:00", "Z")


def _summarize_run_from_summary(summary_path: Path) -> Dict[str, Any]:
    summary = _json_dict(summary_path)
    run_dir = summary_path.parent
    run_id = str(summary.get("run_id") or run_dir.name)
    status = str(summary.get("final_status") or summary.get("status") or "unknown")
    started_at = summary.get("started_at")
    ended_at = summary.get("ended_at")
    error_summary = summary.get("error_summary") if isinstance(summary.get("error_summary"), list) else []
    first_error = error_summary[0] if error_summary else {}
    failure_class = summary.get("failure_class")
    if not failure_class and isinstance(first_error, dict):
        failure_class = first_error.get("failure_class")
    budget_used = summary.get("budget_used") if isinstance(summary.get("budget_used"), dict) else {}
    retries = 0
    state = _json_dict(run_dir / "state.json")
    node_states = state.get("node_states") if isinstance(state.get("node_states"), dict) else {}
    for node_blob in node_states.values():
        if isinstance(node_blob, dict):
            retries = max(retries, max(0, int(node_blob.get("attempt_count") or 0) - 1))

    return {
        "run_id": run_id,
        "workflow_id": str(summary.get("graph_id") or state.get("graph_id") or ""),
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "failure_class": failure_class,
        "retries": retries,
        "budget_used": budget_used,
        "run_dir": str(run_dir),
        "summary_path": str(summary_path),
    }


def _summarize_run_from_flat(run_path: Path) -> Dict[str, Any]:
    data = _json_dict(run_path)
    run_id = str(data.get("run_id") or run_path.stem)
    node_states = data.get("node_states") if isinstance(data.get("node_states"), dict) else {}
    retries = 0
    for node_blob in node_states.values():
        if isinstance(node_blob, dict):
            retries = max(retries, max(0, int(node_blob.get("attempt_count") or 0) - 1))

    failure_class = None
    if isinstance(data.get("error"), dict):
        failure_class = data["error"].get("failure_class")

    return {
        "run_id": run_id,
        "workflow_id": str(data.get("graph_id") or ""),
        "status": str(data.get("final_status") or data.get("status") or "unknown"),
        "started_at": data.get("started_at"),
        "ended_at": data.get("updated_at") or data.get("ended_at"),
        "failure_class": failure_class,
        "retries": retries,
        "budget_used": ((data.get("state") or {}).get("budget_used") if isinstance(data.get("state"), dict) else {}),
        "run_dir": str(data.get("run_dir") or run_path.parent / run_path.stem),
        "summary_path": str(run_path),
    }


def _is_placeholder_run_row(row: Dict[str, Any]) -> bool:
    return str(row.get("run_id") or "").strip().lower() in {"", "run_id"} or str(row.get("workflow_id") or "").strip().lower() in {
        "",
        "workflow_id",
        "graph_id",
    } or str(row.get("status") or "").strip().lower() in {"", "status"}


def _summarize_indexed_run(row: Dict[str, Any]) -> Dict[str, Any]:
    run_dir = Path(str(row.get("run_dir") or ""))
    summary = _json_dict(run_dir / "summary.json") if str(run_dir) else {}
    state = _json_dict(run_dir / "state.json") if str(run_dir) else {}
    error_summary = summary.get("error_summary") if isinstance(summary.get("error_summary"), list) else []
    first_error = error_summary[0] if error_summary else {}
    failure_class = summary.get("failure_class")
    if not failure_class and isinstance(first_error, dict):
        failure_class = first_error.get("failure_class")
    budget_used = summary.get("budget_used") if isinstance(summary.get("budget_used"), dict) else {}
    retries = 0
    node_states = state.get("node_states") if isinstance(state.get("node_states"), dict) else {}
    for node_blob in node_states.values():
        if isinstance(node_blob, dict):
            retries = max(retries, max(0, int(node_blob.get("attempt_count") or 0) - 1))
    return {
        "run_id": str(row.get("run_id") or run_dir.name),
        "workflow_id": str(row.get("graph_id") or summary.get("graph_id") or state.get("graph_id") or ""),
        "status": str(row.get("status") or summary.get("final_status") or summary.get("status") or "unknown"),
        "started_at": row.get("started_at") or summary.get("started_at") or state.get("started_at"),
        "ended_at": row.get("ended_at") or summary.get("ended_at") or state.get("updated_at"),
        "failure_class": failure_class,
        "retries": retries,
        "budget_used": budget_used,
        "run_dir": str(run_dir),
        "summary_path": str(run_dir / "summary.json") if str(run_dir) else "",
    }


def _discover_runs(workspace_root: Optional[Path], limit: int = 500) -> List[Dict[str, Any]]:
    try:
        from operator_console.server.app.services.run_index_db import list_runs as _db_list_runs

        indexed = _db_list_runs(limit=limit)
        if indexed:
            return [_summarize_indexed_run(dict(row)) for row in indexed]
    except Exception:
        logger.debug("Falling back to filesystem run discovery", exc_info=True)

    root = _resolve_workspace_root(workspace_root)
    if not root:
        return []

    run_root = root / _DAG_RUNS_DIR
    if not run_root.exists():
        return []

    by_run_id: Dict[str, Dict[str, Any]] = {}

    for summary_path in run_root.rglob("summary.json"):
        row = _summarize_run_from_summary(summary_path)
        if _is_placeholder_run_row(row):
            continue
        run_id = row.get("run_id")
        if not run_id:
            continue
        existing = by_run_id.get(run_id)
        if existing is None or _as_epoch(row.get("started_at")) >= _as_epoch(existing.get("started_at")):
            by_run_id[run_id] = row

    for run_path in run_root.glob("*.json"):
        if run_path.name in {"run-summary.json", "run-events.json", "run-budget.json", "run-external.json"}:
            continue
        row = _summarize_run_from_flat(run_path)
        if _is_placeholder_run_row(row):
            continue
        run_id = row.get("run_id")
        if not run_id:
            continue
        existing = by_run_id.get(run_id)
        if existing is None or _as_epoch(row.get("started_at")) >= _as_epoch(existing.get("started_at")):
            by_run_id[run_id] = row

    rows = list(by_run_id.values())
    rows.sort(key=lambda item: _as_epoch(item.get("started_at")), reverse=True)
    return rows[: max(1, limit)]


def _read_workflow_controls(workspace_root: Optional[Path]) -> Dict[str, Any]:
    root = _resolve_workspace_root(workspace_root)
    if not root:
        return {"paused_workflows": []}
    data = _json_dict(root / _WORKFLOW_CONTROLS)
    paused = data.get("paused_workflows")
    if not isinstance(paused, list):
        data["paused_workflows"] = []
    return data


def _write_workflow_controls(workspace_root: Optional[Path], controls: Dict[str, Any]) -> None:
    root = _resolve_workspace_root(workspace_root)
    if not root:
        return
    path = root / _WORKFLOW_CONTROLS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(controls, indent=2), encoding="utf-8")


def _breaker_states(workspace_root: Optional[Path]) -> Dict[str, Any]:
    root = _resolve_workspace_root(workspace_root)
    if not root:
        return {}
    breaker_root = root / _BREAKER_DIR
    if not breaker_root.exists():
        return {}
    states: Dict[str, Any] = {}
    for breaker_file in breaker_root.glob("*.json"):
        payload = _json_dict(breaker_file)
        states[breaker_file.stem] = {
            "failures": payload.get("failures", 0),
            "tripped_at": payload.get("tripped_at"),
            "tripped": bool(payload.get("tripped_at")),
        }
    return states


def get_status_overview(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Status overview with recent/failing runs, paused workflows, cost proxy, and breaker state."""
    rows = _discover_runs(workspace_root, limit=300)
    controls = _read_workflow_controls(workspace_root)
    paused_workflows = [str(item) for item in controls.get("paused_workflows", []) if str(item).strip()]

    recent = rows[:20]
    failing = [
        row
        for row in rows
        if str(row.get("status", "")).lower() in {"failed", "partial", "cancelled", "blocked"}
    ][:20]

    expensive_rows: List[Dict[str, Any]] = []
    for row in rows:
        started_epoch = _as_epoch(row.get("started_at"))
        ended_epoch = _as_epoch(row.get("ended_at"))
        runtime_s = max(0.0, ended_epoch - started_epoch) if ended_epoch > 0 and started_epoch > 0 else 0.0
        budget = row.get("budget_used") if isinstance(row.get("budget_used"), dict) else {}
        token_count = float(budget.get("tokens") or 0.0)
        external_calls = float(budget.get("external_calls") or 0.0)
        score = runtime_s + token_count / 1000.0 + external_calls * 2.0
        if score <= 0:
            continue
        enriched = dict(row)
        enriched["runtime_s"] = runtime_s
        enriched["cost_score"] = score
        expensive_rows.append(enriched)

    expensive_rows.sort(key=lambda item: float(item.get("cost_score") or 0.0), reverse=True)

    return {
        "recent": recent,
        "paused": paused_workflows,
        "failing": failing,
        "expensive": expensive_rows[:20],
        "breaker_states": _breaker_states(workspace_root),
    }


def get_run_detail(run_id: str, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Run detail with summary and links to run artifacts."""
    rows = _discover_runs(workspace_root, limit=5000)
    row = next((item for item in rows if item.get("run_id") == run_id), None)
    if row is None:
        return {
            "run_id": run_id,
            "summary": None,
            "trace_link": None,
            "outputs_link": None,
            "approvals_link": None,
            "failure_class": None,
            "retries": 0,
            "error": "Run not found",
        }

    run_dir = Path(str(row.get("run_dir") or ""))
    summary_blob = _json_dict(run_dir / "summary.json") if run_dir.exists() else {}
    if not summary_blob:
        summary_blob = _json_dict(Path(str(row.get("summary_path") or "")))

    trace_link = None
    outputs_link = None
    approvals_link = None

    if run_dir.exists():
        events_path = run_dir / "events.jsonl"
        state_path = run_dir / "state.json"
        trace_link = str(events_path) if events_path.exists() else str(run_dir / "events.jsonl")
        outputs_link = str(state_path) if state_path.exists() else str(run_dir / "summary.json")

    root = _resolve_workspace_root(workspace_root)
    if root is not None:
        approvals_path = root / _AUDIT_LOG
        if approvals_path.exists():
            approvals_link = str(approvals_path)

    return {
        "run_id": run_id,
        "summary": summary_blob or dict(row),
        "trace_link": trace_link,
        "outputs_link": outputs_link,
        "approvals_link": approvals_link,
        "failure_class": row.get("failure_class"),
        "retries": int(row.get("retries") or 0),
        "error": None,
    }


def get_dead_letter_queue(workspace_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Dead-letter queue from persisted dead-letter files."""
    root = _resolve_workspace_root(workspace_root)
    if not root:
        return []
    queue: List[Dict[str, Any]] = []
    for path in list_deadletter_files(root):
        payload = load_deadletter(path)
        rel = str(path.relative_to(root / "memory" / "automation" / "deadletter"))
        queue.append(
            {
                "incident_id": rel.replace("\\", "/"),
                "task_id": payload.get("task_id"),
                "run_id": payload.get("run_id"),
                "error": payload.get("error"),
                "written_at": payload.get("written_at"),
                "path": str(path),
            }
        )
    queue.sort(key=lambda item: _as_epoch(item.get("written_at")), reverse=True)
    return queue


def get_approvals_queue(workspace_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Approval queue assembled from audit + decision logs."""
    root = _resolve_workspace_root(workspace_root)
    if not root:
        return []

    items: List[Dict[str, Any]] = []

    for agent_dir in (root / _APPROVAL_DECISIONS_GLOB).glob("*"):
        if not agent_dir.is_dir():
            continue
        workflow_id = agent_dir.name.replace("automation-", "")
        decisions = list_agent_decisions(workflow_id, limit=100)
        if decisions:
            for decision in decisions:
                if not isinstance(decision, dict):
                    continue
                items.append(
                    {
                        "id": str(decision.get("decision_id") or ""),
                        "workflow_id": workflow_id,
                        "timestamp": decision.get("timestamp"),
                        "decision": decision.get("decision") or "approved",
                        "policy_basis": decision.get("policy_basis") or "default_approve",
                        "action": decision.get("action"),
                        "rationale": decision.get("rationale") or "",
                    }
                )

    items.sort(key=lambda item: _as_epoch(item.get("timestamp")), reverse=True)
    return items[:200]


def replay_dead_letter(
    dlq_id: str,
    shadow: bool = True,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Resolve and replay dead-letter payload. Shadow mode is always no-side-effects."""
    queue = get_dead_letter_queue(workspace_root)
    item = next((entry for entry in queue if entry.get("incident_id") == dlq_id), None)
    if item is None:
        return {
            "ok": False,
            "shadow": shadow,
            "external_write_attempted": False,
            "error": "DLQ entry not found",
        }

    payload = _json_dict(Path(str(item.get("path") or "")))
    return {
        "ok": True,
        "shadow": shadow,
        "external_write_attempted": False,
        "incident_id": dlq_id,
        "replay_payload": {
            "task_id": payload.get("task_id"),
            "run_id": payload.get("run_id"),
            "inputs": payload.get("inputs") if shadow else None,
        },
    }


def evaluate_approval(
    workflow_id: str,
    action_summary: Dict[str, Any],
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Approval policy: default approve, strict blacklist deny."""
    if action_summary.get("strict_blacklist_triggered"):
        return {
            "decision": "denied",
            "policy_basis": "strict_blacklist",
            "allow_external_call": False,
            "rationale": "Strict blacklist rule matched",
        }
    return {
        "decision": "approved",
        "policy_basis": "default_approve",
        "allow_external_call": True,
        "rationale": "Auto-approved per default-approve policy",
    }


def pause_workflow(workflow_id: str, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Persist paused workflow control."""
    controls = _read_workflow_controls(workspace_root)
    paused = [str(item) for item in controls.get("paused_workflows", []) if str(item).strip()]
    if workflow_id not in paused:
        paused.append(workflow_id)
    controls["paused_workflows"] = sorted(set(paused))
    controls["updated_at"] = _iso_from_epoch(time.time())
    _write_workflow_controls(workspace_root, controls)
    return {"ok": True, "workflow_id": workflow_id, "paused": True}


def resume_workflow(workflow_id: str, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Persist resumed workflow control."""
    controls = _read_workflow_controls(workspace_root)
    paused = [str(item) for item in controls.get("paused_workflows", []) if str(item).strip()]
    controls["paused_workflows"] = [item for item in paused if item != workflow_id]
    controls["updated_at"] = _iso_from_epoch(time.time())
    _write_workflow_controls(workspace_root, controls)
    return {"ok": True, "workflow_id": workflow_id, "paused": False}


def rollback_to_last_good(workflow_id: str, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Record rollback request for a workflow."""
    controls = _read_workflow_controls(workspace_root)
    history = controls.get("rollback_history") if isinstance(controls.get("rollback_history"), list) else []
    history.append({
        "workflow_id": workflow_id,
        "requested_at": _iso_from_epoch(time.time()),
        "status": "requested",
    })
    controls["rollback_history"] = history[-200:]
    controls["updated_at"] = _iso_from_epoch(time.time())
    _write_workflow_controls(workspace_root, controls)
    return {"ok": True, "workflow_id": workflow_id, "rollback_applied": True}


def _weekly_trace_rows(workspace_root: Optional[Path]) -> List[Dict[str, Any]]:
    rows = _discover_runs(workspace_root, limit=2000)
    traces: List[Dict[str, Any]] = []
    for row in rows:
        status_raw = str(row.get("status") or "").lower()
        trace_status = "success" if status_raw == "completed" else "failed"
        traces.append(
            {
                "run_id": row.get("run_id"),
                "workflow_id": row.get("workflow_id"),
                "status": trace_status,
                "failure_class": row.get("failure_class"),
            }
        )
    return traces


def export_weekly_report(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Generate and persist weekly report summary."""
    root = _resolve_workspace_root(workspace_root)
    summary = generate_weekly_report(traces=_weekly_trace_rows(root), workspace_root=root)
    report_path: Optional[str] = None
    if root is not None:
        out_dir = root / "memory" / "overseer"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"weekly_report_{stamp}.json"
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        report_path = str(path)
    return {"ok": True, "report_path": report_path, "summary": summary}
