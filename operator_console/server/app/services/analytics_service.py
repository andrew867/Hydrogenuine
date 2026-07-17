"""Run analytics: budget_used, counts, event type counts, node summary from run_dir."""

import json
from pathlib import Path
from .run_index_db import get_run


def _run_dir(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])


def get_analytics(run_id: str) -> dict:
    """
    Return { ok: True, budget_used, counts, event_counts, node_summary } or { ok: False, error }.
    Aggregates from summary.json, state.json, and events.jsonl.
    """
    try:
        rd = _run_dir(run_id)
    except FileNotFoundError:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}

    budget_used = None
    counts = None
    summary = None
    if (rd / "summary.json").exists():
        try:
            summary = json.loads((rd / "summary.json").read_text(encoding="utf-8"))
            budget_used = summary.get("budget_used")
            counts = summary.get("counts", {})
        except (json.JSONDecodeError, OSError):
            pass

    event_counts = {}
    path = rd / "events.jsonl"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n\r")
                    if line:
                        try:
                            obj = json.loads(line)
                            ev = obj.get("event", "unknown")
                            event_counts[ev] = event_counts.get(ev, 0) + 1
                        except json.JSONDecodeError:
                            event_counts["_raw"] = event_counts.get("_raw", 0) + 1
        except OSError:
            pass

    node_summary = []
    state_path = rd / "state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            raw = state.get("nodes") or state.get("node_states")
            if isinstance(raw, dict):
                raw = [{"id": k, **(v if isinstance(v, dict) else {})} for k, v in raw.items()]
            if isinstance(raw, list):
                for n in raw:
                    if not isinstance(n, dict):
                        continue
                    node_id = n.get("id")
                    status = n.get("status")
                    err = n.get("error")
                    code = err.get("code") if isinstance(err, dict) else (err if err else None)
                    node_summary.append({"id": node_id, "status": status, "error_code": code})
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    return {
        "ok": True,
        "budget_used": budget_used,
        "counts": counts or {},
        "event_counts": event_counts,
        "node_summary": node_summary,
        "final_status": summary.get("final_status") if summary else None,
    }
