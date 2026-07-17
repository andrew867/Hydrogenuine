"""Ownership chain, events, search, and edges for operator console. Uses run_dir/ownership.db."""

from pathlib import Path

_workspace_root = Path(__file__).resolve().parents[4]
if str(_workspace_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_workspace_root))

from .run_index_db import get_run


def _ownership_db_path(run_id: str) -> Path | None:
    r = get_run(run_id)
    if not r or not r.get("run_dir"):
        return None
    return Path(r["run_dir"]) / "ownership.db"


def get_ownership_chain(run_id: str, task_id: str | None = None) -> dict:
    """Return { ok, run_id, chain[], error? }. Chain is list of { task_id, sponsor_id, accountable_id, executor_id, approver_id, state, updated_ts }."""
    db_path = _ownership_db_path(run_id)
    if not db_path:
        return {"ok": False, "run_id": run_id, "chain": [], "error": "run not found"}
    if not db_path.exists():
        return {"ok": True, "run_id": run_id, "chain": []}
    try:
        from hg_core.ownership import ownership_db
        ownership_db.init_ownership_schema(str(db_path))
        rows = ownership_db.get_chain(str(db_path), run_id, task_id=task_id)
        return {"ok": True, "run_id": run_id, "chain": [dict(r) for r in rows]}
    except Exception as e:
        return {"ok": False, "run_id": run_id, "chain": [], "error": str(e)}


def get_ownership_edges(run_id: str, task_id: str | None = None) -> dict:
    """Return { ok, run_id, edges[], error? }."""
    db_path = _ownership_db_path(run_id)
    if not db_path:
        return {"ok": False, "run_id": run_id, "edges": [], "error": "run not found"}
    if not db_path.exists():
        return {"ok": True, "run_id": run_id, "edges": []}
    try:
        from hg_core.ownership import ownership_db
        ownership_db.init_ownership_schema(str(db_path))
        rows = ownership_db.get_chain_edges(str(db_path), run_id, task_id=task_id)
        return {"ok": True, "run_id": run_id, "edges": [dict(r) for r in rows]}
    except Exception as e:
        return {"ok": False, "run_id": run_id, "edges": [], "error": str(e)}


def get_ownership_events(run_id: str, task_id: str | None = None, limit: int = 100) -> dict:
    """Return { ok, run_id, events[], error? }."""
    db_path = _ownership_db_path(run_id)
    if not db_path:
        return {"ok": False, "run_id": run_id, "events": [], "error": "run not found"}
    if not db_path.exists():
        return {"ok": True, "run_id": run_id, "events": []}
    try:
        from hg_core.ownership import ownership_db
        ownership_db.init_ownership_schema(str(db_path))
        rows = ownership_db.ledger_list_events(str(db_path), run_id, task_id=task_id, limit=limit)
        return {"ok": True, "run_id": run_id, "events": rows}
    except Exception as e:
        return {"ok": False, "run_id": run_id, "events": [], "error": str(e)}


def search_ownership_events(run_id: str, q: str, task_id: str | None = None, limit: int = 50) -> dict:
    """Full-text search over ownership events. Returns { ok, run_id, hits[], error? }."""
    db_path = _ownership_db_path(run_id)
    if not db_path:
        return {"ok": False, "run_id": run_id, "hits": [], "error": "run not found"}
    if not db_path.exists():
        return {"ok": True, "run_id": run_id, "hits": []}
    if not q or not q.strip():
        return {"ok": True, "run_id": run_id, "hits": []}
    try:
        from hg_core.ownership import ownership_db
        ownership_db.init_ownership_schema(str(db_path))
        rows = ownership_db.search_events_fts(str(db_path), run_id, q.strip(), task_id=task_id, limit=limit)
        return {"ok": True, "run_id": run_id, "hits": rows}
    except Exception as e:
        return {"ok": False, "run_id": run_id, "hits": [], "error": str(e)}


def get_ownership_availability(run_id: str) -> dict:
    """Placeholder: availability is executor-side (in-memory). Returns { ok, run_id, principals[] }."""
    return {"ok": True, "run_id": run_id, "principals": [], "note": "Availability is managed by the executor (in-memory)."}
