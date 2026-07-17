"""Generate incident report from run_dir delegation and behavior artifacts (Autonomy Ch5)."""

import json
from pathlib import Path
from typing import Any, Dict

from .run_index_db import get_run


def _run_dir(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])


def generate_incident_report(run_id: str) -> Dict[str, Any]:
    """
    Build incident report from delegation_summary.json, delegation_graph.json, behavior_events.jsonl.
    Returns { ok: True, report: { run_id, workflow_id, metrics, anomalies, intervention, final_state, ... } }
    or { ok: False, error: { code, message } }.
    """
    try:
        rd = _run_dir(run_id)
    except FileNotFoundError:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    summary_path = rd / "delegation_summary.json"
    graph_path = rd / "delegation_graph.json"
    events_path = rd / "behavior_events.jsonl"
    if not summary_path.exists():
        return {"ok": False, "error": {"code": "MISSING", "message": "delegation_summary.json not found"}}
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": {"code": "INVALID", "message": str(e)}}
    graph = None
    if graph_path.exists():
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    events_count = 0
    if events_path.exists():
        try:
            events_count = sum(1 for _ in events_path.open(encoding="utf-8") if _.strip())
        except OSError:
            pass
    report = {
        "run_id": run_id,
        "workflow_id": summary.get("workflow_id", ""),
        "root_objective_summary": summary.get("root_objective_summary", ""),
        "metrics": summary.get("metrics", {}),
        "anomalies": summary.get("anomalies", []),
        "quality": summary.get("quality", {}),
        "intervention": summary.get("intervention", {}),
        "final_state": summary.get("final_state", {}),
        "top_bottlenecks": summary.get("top_bottlenecks", []),
        "behavior_events_count": events_count,
        "has_graph": graph is not None,
    }
    if graph:
        report["node_count"] = len(graph.get("nodes", []))
        report["edge_count"] = len(graph.get("edges", []))
    return {"ok": True, "report": report}


def incident_report_md(run_id: str) -> str:
    """Return incident report as Markdown string for export."""
    res = generate_incident_report(run_id)
    if not res.get("ok"):
        return f"# Incident Report\n\nError: {res.get('error', {}).get('message', 'unknown')}"
    r = res["report"]
    lines = [
        "# Incident Report",
        f"**Run ID:** {r['run_id']}",
        f"**Workflow:** {r['workflow_id']}",
        "",
        "## Final state",
        f"- Status: {r['final_state'].get('status', '')}",
        f"- External writes attempted: {r['final_state'].get('external_writes_attempted', '')}",
        f"- External writes blocked: {r['final_state'].get('external_writes_blocked', '')}",
        "",
        "## Metrics",
    ]
    for k, v in (r.get("metrics") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Anomalies"])
    for a in r.get("anomalies") or []:
        lines.append(f"- **{a.get('detector_id', '')}** ({a.get('severity', '')}): {a.get('recommended_action', '')}")
        for ev in a.get("evidence", []):
            lines.append(f"  - {ev.get('pointer', '')}: {ev.get('value', '')}")
    lines.extend(["", "## Intervention", f"- Step: {r.get('intervention', {}).get('step', '')}", f"- Exceeded budget: {r.get('intervention', {}).get('exceeded_budget', '')}"])
    lines.extend(["", "## Quality", f"- Score: {r.get('quality', {}).get('score', '')}", f"- Degraded: {r.get('quality', {}).get('degraded', '')}"])
    return "\n".join(lines)
