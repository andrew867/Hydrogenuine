from pathlib import Path
import json
from .run_index_db import list_runs as _list, get_run as _get, set_status
from .run_lineage import build_run_lineage_summary
from .worker_adapter import resume_inprocess

def list_runs(limit: int = 5000):
    return {"ok": True, "runs": _list(limit=max(1, min(limit, 10000)))}

def get_run(run_id: str):
    r = _get(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    lineage_summary = build_run_lineage_summary(run_id, run_record=r)
    run_dir = r.get("run_dir")
    if not run_dir or not isinstance(run_dir, (str, Path)):
        # Run exists in index (e.g. blocked) but has no run_dir; return record so detail page can show it
        out = {"ok": True, **r, "summary": None, "graph": None, "run_dir_missing": True, "lineage_summary": lineage_summary}
        if str(r.get("status") or "") == "blocked" and not (r.get("blocked_reason") or "").strip():
            try:
                from hg_core.gate import get_release_gate_status
                gate = get_release_gate_status(workflow_family=str(r.get("graph_id") or ""), target_kind="workflow", target_id=str(r.get("graph_id") or ""))
                out["blocked_reason"] = gate.get("reason") or "blocked by release gate"
            except Exception:
                out["blocked_reason"] = "blocked by governance (release gate or policy)"
        return out
    rd = Path(run_dir)
    summary = None
    if (rd / "summary.json").exists():
        summary = json.loads((rd / "summary.json").read_text(encoding="utf-8"))
    graph = None
    if (rd / "graph.json").exists():
        graph = json.loads((rd / "graph.json").read_text(encoding="utf-8"))
    return {"ok": True, **r, "summary": summary, "graph": graph, "lineage_summary": lineage_summary}

def resume_run(run_id: str):
    r = _get(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    run_dir = r.get("run_dir")
    if not run_dir:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run has no run_dir"}}
    res = resume_inprocess(run_id, run_dir)
    set_status(run_id, res.get("status","unknown"))
    return {"ok": True, "run_id": run_id, "status": res.get("status","unknown")}


def approve_run(run_id: str):
    """Mark a pending_approval run as approved; scheduler will pick it up and launch."""
    r = _get(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    if str(r.get("status") or "") != "pending_approval":
        return {"ok": False, "error": {"code": "INVALID_STATE", "message": "run is not pending approval"}}
    set_status(run_id, "approved_pending_launch")
    return {"ok": True, "run_id": run_id, "message": "Run approved; scheduler will launch shortly."}


def deny_run(run_id: str, reason: str | None = None):
    """Mark a pending_approval run as denied (blocked)."""
    r = _get(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    if str(r.get("status") or "") != "pending_approval":
        return {"ok": False, "error": {"code": "INVALID_STATE", "message": "run is not pending approval"}}
    set_status(run_id, "blocked", blocked_reason=reason or "denied by operator")
    return {"ok": True, "run_id": run_id, "message": "Run denied."}
