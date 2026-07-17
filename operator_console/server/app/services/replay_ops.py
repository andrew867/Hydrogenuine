"""Replay run from recordings (Phase 3)."""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from ..core.config import settings
from .run_index_db import bulk_cancel_gate_queue_stubs, get_run, list_cancellable_run_ids, upsert_run, set_status

# Optional: use hg_core replay when workspace on path
try:
    import sys
    _workspace_root = Path(__file__).resolve().parents[4]
    if str(_workspace_root) not in sys.path:
        sys.path.insert(0, str(_workspace_root))
    from hg_core.task_graph import DAG, TaskGraphExecutor
    from hg_core.task_graph.state_store import StateStore
    from hg_core.task_graph.tool_contract_setup import build_default_tool_contract
    from hg_core.task_graph.replay_dispatcher import make_replay_adapter
    _replay_available = True
except Exception:
    _replay_available = False


def replay_run(run_id: str) -> dict:
    """Run executor with replay dispatcher using run_dir recordings; create new run for replay output."""
    if not _replay_available:
        return {
            "ok": False,
            "error": {
                "code": "HG_CORE_REQUIRED",
                "message": "Replay requires hg_core installed.",
                "remediation": "Install the workspace package (pip install -e .) and ensure HG_WORKSPACE points to a repo with hg_core. See docs/guides/SETUP_GUIDE_FOR_BEGINNERS.md or docs/runbooks/OPERATOR_REPLAY_FORK.md.",
            },
        }
    r = get_run(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    run_dir = Path(r["run_dir"])
    recordings = run_dir / "recordings" / "attempts.jsonl"
    if not recordings.exists():
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "no recordings (recordings/attempts.jsonl) for this run"}}
    graph_path = run_dir / "graph.reviewed.json" if (run_dir / "graph.reviewed.json").exists() else run_dir / "graph.json"
    if not graph_path.exists():
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "graph.json not found"}}
    dag_dict = json.loads(graph_path.read_text(encoding="utf-8"))
    dag = DAG.from_dict(dag_dict)
    new_run_id = str(uuid.uuid4())
    root = Path(settings.runs_root)
    root.mkdir(parents=True, exist_ok=True)
    new_run_dir = root / new_run_id
    new_run_dir.mkdir(parents=True, exist_ok=True)
    state_store = StateStore(base_dir=root)
    dispatcher = make_replay_adapter(str(run_dir))
    registry, adapter = build_default_tool_contract()
    executor = TaskGraphExecutor(
        state_store=state_store,
        dispatcher=dispatcher,
        tool_registry=registry,
        tool_adapter=adapter,
    )
    result = executor.run(dag, run_id=new_run_id, run_dir=new_run_dir)
    if result.get("ok") is False:
        return {"ok": False, "error": {"code": "REPLAY_FAILED", "message": result.get("error", "replay failed")}}
    run_state = result.get("run_state", {})
    upsert_run({
        "run_id": new_run_id,
        "graph_id": result.get("graph_id"),
        "status": result.get("status", "completed"),
        "started_at": run_state.get("started_at"),
        "ended_at": run_state.get("updated_at"),
        "run_dir": str(new_run_dir),
    })
    return {"ok": True, "run_id": new_run_id, "status": result.get("status", "completed"), "run_dir": str(new_run_dir)}


def cancel_run(run_id: str) -> dict:
    """Set run status to cancelled in index; stop process and release lease when hg_realtime is available."""
    r = get_run(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    canonical_id = r.get("run_id") or run_id
    try:
        from hg_realtime.leases.store import default_lease_store
        from hg_realtime.integrations.cancel import cancel_run as hg_cancel_run
        lease_store = default_lease_store()
        result = hg_cancel_run(canonical_id, lease_store, set_status=set_status)
        if not result.get("ok"):
            set_status(canonical_id, "cancelled")
        run_dir = Path(r.get("run_dir") or "")
        if run_dir:
            try:
                run_dir.mkdir(parents=True, exist_ok=True)
                payload = {
                    "run_id": canonical_id,
                    "requested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "reason": "operator cancel",
                    "source": "operator_console",
                }
                (run_dir / "cancel.requested.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            except OSError:
                pass
        return {"ok": True, "run_id": canonical_id, "status": "cancelled"}
    except ImportError:
        set_status(canonical_id, "cancelled")
        run_dir = Path(r.get("run_dir") or "")
        if run_dir:
            try:
                run_dir.mkdir(parents=True, exist_ok=True)
                payload = {
                    "run_id": canonical_id,
                    "requested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "reason": "operator cancel",
                    "source": "operator_console",
                }
                (run_dir / "cancel.requested.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            except OSError:
                pass
        return {"ok": True, "run_id": canonical_id, "status": "cancelled"}


def cancel_stale_runs(stale_minutes: int = 0) -> dict:
    """Cancel active runs and gate-queue stubs.

    stale_minutes=0 (default): cancel all running/launching/pending gate rows.
    stale_minutes>0: only cancel rows older than that threshold.
    """
    stub_count = bulk_cancel_gate_queue_stubs()
    active_ids = list_cancellable_run_ids(stale_minutes=stale_minutes)
    cancelled = []
    errors = []
    for run_id in active_ids:
        out = cancel_run(run_id)
        if out.get("ok"):
            cancelled.append(out.get("run_id") or run_id)
        else:
            errors.append({"run_id": run_id, "error": out.get("error")})
    total = stub_count + len(cancelled)
    return {
        "ok": True,
        "cancelled": cancelled,
        "count": total,
        "stale_found": stub_count + len(active_ids),
        "stub_cancelled": stub_count,
        "active_cancelled": len(cancelled),
        "stale_minutes": stale_minutes,
        "errors": errors if errors else None,
    }
