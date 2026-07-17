from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.config import settings

_DISCOVERY_CACHE: dict[str, Any] = {"expires_at": 0.0, "limit": 0, "rows": []}


def reset_caches_for_tests() -> None:
    """Clear the module-level run-discovery TTL cache. Test-isolation helper only.

    ``_DISCOVERY_CACHE`` holds run rows with a multi-second/minute TTL; across tests
    (which run within the TTL) a prior test's run rows leak into a later test's entity
    listing, producing stale identity/decision state (OSI2/OEP3 entity/persona
    victims). Resetting per test restores isolation; production behaviour is unchanged
    (the cache still populates/expires normally in a running server)."""
    _DISCOVERY_CACHE.update({"expires_at": 0.0, "limit": 0, "rows": []})


def _conn():
    from hg_gateway.db import get_connection

    return get_connection()


def _row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    keys = getattr(row, "keys", None)
    if callable(keys):
        return {key: row[key] for key in row.keys()}
    return dict(row)


def _run_discovery_ttl_seconds() -> float:
    raw = (os.environ.get("HG_RUN_DISCOVERY_CACHE_TTL") or "15").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 15.0


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        pass
    raw = os.environ.get("HG_WORKSPACE", "").strip()
    if raw:
        p = Path(raw)
        if p.exists():
            return p
    return None


def _json_dict(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
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


def _infer_run_from_dir(run_dir: Path) -> dict[str, Any]:
    summary = _json_dict(run_dir / "summary.json")
    state = _json_dict(run_dir / "state.json")
    graph = _json_dict(run_dir / "graph.json")

    summary_run_id = str(summary.get("run_id") or "") or str(state.get("run_id") or "")
    run_id = run_dir.name or summary_run_id
    graph_id = summary.get("graph_id") or state.get("graph_id") or graph.get("graph_id")
    status = summary.get("final_status") or summary.get("status") or state.get("final_status") or state.get("status") or "unknown"
    started_at = summary.get("started_at") or state.get("started_at")
    ended_at = summary.get("ended_at") or summary.get("updated_at") or state.get("updated_at")
    if _as_epoch(started_at) <= 0:
        try:
            started_at = run_dir.stat().st_mtime
        except OSError:
            started_at = 0.0

    return {
        "run_id": str(run_id),
        "artifact_run_id": summary_run_id or None,
        "graph_id": graph_id,
        "status": str(status),
        "started_at": _as_epoch(started_at),
        "ended_at": _as_epoch(ended_at) if _as_epoch(ended_at) > 0 else None,
        "run_dir": str(run_dir),
        "correlation_id": summary.get("correlation_id") or state.get("correlation_id"),
    }


def _is_placeholder_run_id(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"run_id", "graph_id", "status", "started_at", "ended_at", "correlation_id", "run_dir"}


def _is_placeholder_value(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {
        "",
        "run_id",
        "graph_id",
        "status",
        "started_at",
        "ended_at",
        "correlation_id",
        "run_dir",
        "workflow_id",
    }


def _is_valid_discovered_run(row: dict[str, Any]) -> bool:
    run_id = row.get("run_id")
    graph_id = row.get("graph_id")
    status = row.get("status")
    if _is_placeholder_run_id(run_id):
        return False
    if _is_placeholder_value(graph_id):
        return False
    if _is_placeholder_value(status):
        return False
    run_dir = row.get("run_dir")
    if run_dir and _is_placeholder_value(run_dir):
        return False
    return True


_TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "cancelled", "partial", "success"})
_ACTIVE_RUN_STATUSES = frozenset(
    {"running", "launching", "approved_pending_launch", "pending_approval", "pending", "blocked"}
)


def _merge_run_rows(primary: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    for key in ("graph_id", "status", "started_at", "ended_at", "run_dir", "correlation_id", "artifact_run_id"):
        current = merged.get(key)
        candidate = incoming.get(key)
        if current in (None, "", 0) and candidate not in (None, "", 0):
            merged[key] = candidate
    cur_status = str(merged.get("status") or "").strip().lower()
    inc_status = str(incoming.get("status") or "").strip().lower()
    should_take_disk_terminal = (
        inc_status in _TERMINAL_RUN_STATUSES
        and (
            cur_status in _ACTIVE_RUN_STATUSES
            or (cur_status == "failed" and inc_status in {"cancelled", "completed"})
        )
    )
    if should_take_disk_terminal:
        merged["status"] = incoming.get("status")
        inc_ended = incoming.get("ended_at")
        if inc_ended not in (None, "", 0):
            merged["ended_at"] = inc_ended
    return merged


def _is_gate_queue_stub(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or "").strip().lower()
    if not str(row.get("run_dir") or "").strip():
        if status in {"pending_approval", "blocked", "launching", "approved_pending_launch"}:
            return True
    if status == "blocked" and str(row.get("blocked_reason") or "").strip():
        return True
    return False


_ACTIVE_RUN_STATUSES = (
    "running",
    "launching",
    "approved_pending_launch",
    "pending_approval",
    "pending",
)


def bulk_cancel_gate_queue_stubs() -> int:
    """Mark gate-queue stub rows cancelled without per-run process teardown."""
    import time

    init_db()
    now = time.time()
    with _conn() as c:
        stub_rows = c.execute(
            """
            SELECT run_id FROM runs
            WHERE COALESCE(run_dir, '') = ''
              AND status IN ('blocked', 'pending_approval', 'approved_pending_launch', 'launching')
            """
        ).fetchall()
        count = len(stub_rows or [])
        if count:
            c.execute(
                """
                UPDATE runs
                SET status = 'cancelled', ended_at = ?
                WHERE COALESCE(run_dir, '') = ''
                  AND status IN ('blocked', 'pending_approval', 'approved_pending_launch', 'launching')
                """,
                (now,),
            )
    _DISCOVERY_CACHE.update({"expires_at": 0.0, "limit": 0, "rows": []})
    return count


def list_cancellable_run_ids(*, stale_minutes: int = 0) -> list[str]:
    """Return run_ids that are active or gate-queue stubs and eligible for cancellation."""
    init_db()
    import time

    cutoff = time.time() - (max(0, int(stale_minutes)) * 60)
    run_ids: list[str] = []
    with _conn() as c:
        rows = c.execute(
            f"""
            SELECT run_id, status, started_at, ended_at, run_dir, blocked_reason
            FROM runs
            WHERE COALESCE(run_dir, '') != ''
              AND status IN ({",".join("?" for _ in _ACTIVE_RUN_STATUSES)})
            """,
            _ACTIVE_RUN_STATUSES,
        ).fetchall()
    for row in rows:
        data = _row_to_dict(row)
        run_id = str(data.get("run_id") or "").strip()
        if not run_id:
            continue
        started_ts = _as_epoch(data.get("started_at"))
        if stale_minutes > 0:
            if started_ts > 0 and started_ts > cutoff:
                continue
            status = str(data.get("status") or "").strip().lower()
            ended = data.get("ended_at")
            if status in {"completed", "failed", "cancelled", "partial", "success"} and ended not in (None, "", 0):
                continue
        run_ids.append(run_id)
    return run_ids


def cleanup_invalid_runs() -> dict[str, int]:
    init_db()
    deleted = 0
    merged = 0
    reconciled = 0
    with _conn() as c:
        stub_rows = c.execute(
            """
            SELECT run_id FROM runs
            WHERE status = 'pending_approval'
              AND COALESCE(run_dir, '') = ''
              AND COALESCE(blocked_reason, '') != ''
            """
        ).fetchall()
        reconciled = len(stub_rows or [])
        if reconciled:
            c.execute(
                """
                UPDATE runs
                SET status = 'blocked'
                WHERE status = 'pending_approval'
                  AND COALESCE(run_dir, '') = ''
                  AND COALESCE(blocked_reason, '') != ''
                """
            )
        rows = c.execute("SELECT run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id FROM runs").fetchall()
        by_run_dir: dict[str, dict[str, Any]] = {}
        for row in rows:
            data = _row_to_dict(row)
            run_id = str(data.get("run_id") or "").strip()
            run_dir = str(data.get("run_dir") or "").strip()
            if _is_placeholder_run_id(run_id):
                c.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
                deleted += 1
                continue
            if not run_dir:
                continue
            existing = by_run_dir.get(run_dir)
            if existing is None:
                by_run_dir[run_dir] = data
                continue
            preferred = existing
            duplicate = data
            preferred_has_corr = bool(preferred.get("correlation_id"))
            duplicate_has_corr = bool(duplicate.get("correlation_id"))
            if duplicate_has_corr and not preferred_has_corr:
                preferred, duplicate = duplicate, preferred
            elif preferred_has_corr == duplicate_has_corr:
                preferred_matches_dir = Path(str(preferred.get("run_dir") or "")).name == str(preferred.get("run_id") or "")
                duplicate_matches_dir = Path(str(duplicate.get("run_dir") or "")).name == str(duplicate.get("run_id") or "")
                if duplicate_matches_dir and not preferred_matches_dir:
                    preferred, duplicate = duplicate, preferred
            merged_row = _merge_run_rows(preferred, duplicate)
            c.execute(
                """
                INSERT OR REPLACE INTO runs(run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    merged_row.get("run_id"),
                    merged_row.get("graph_id"),
                    merged_row.get("status"),
                    merged_row.get("started_at"),
                    merged_row.get("ended_at"),
                    merged_row.get("run_dir"),
                    merged_row.get("correlation_id"),
                ),
            )
            c.execute("DELETE FROM runs WHERE run_id=?", (str(duplicate.get("run_id") or ""),))
            merged += 1
            by_run_dir[run_dir] = merged_row
    _DISCOVERY_CACHE.update({"expires_at": 0.0, "limit": 0, "rows": []})
    return {"deleted": deleted, "merged": merged, "reconciled": reconciled}


def _discover_run_rows(limit: int) -> list[dict[str, Any]]:
    if (os.environ.get("HG_DISABLE_RUN_DISCOVERY") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return []
    now = time.time()
    cached_rows = _DISCOVERY_CACHE.get("rows") or []
    cached_limit = int(_DISCOVERY_CACHE.get("limit") or 0)
    expires_at = float(_DISCOVERY_CACHE.get("expires_at") or 0.0)
    if now < expires_at and cached_rows and cached_limit >= limit:
        return list(cached_rows[: max(1, limit)])

    discovered: dict[str, dict[str, Any]] = {}

    def _add(row: dict[str, Any]) -> None:
        rid = str(row.get("run_id") or "").strip()
        if not rid or not _is_valid_discovered_run(row):
            return
        existing = discovered.get(rid)
        if existing is None or _as_epoch(row.get("started_at")) > _as_epoch(existing.get("started_at")):
            discovered[rid] = row

    runs_root = Path(settings.runs_root)
    if runs_root.exists():
        for child in runs_root.iterdir():
            if not child.is_dir():
                continue
            if (child / "summary.json").exists() or (child / "graph.json").exists() or (child / "state.json").exists():
                _add(_infer_run_from_dir(child))

    workspace = _workspace_root()
    if workspace:
        dag_runs_root = workspace / "memory" / "automation" / "dag_runs"
        if dag_runs_root.exists():
            for summary_path in dag_runs_root.rglob("summary.json"):
                _add(_infer_run_from_dir(summary_path.parent))
            for json_path in dag_runs_root.glob("*.json"):
                if json_path.name in {"run-summary.json", "run-events.json", "run-budget.json", "run-external.json"}:
                    continue
                payload = _json_dict(json_path)
                run_id = payload.get("run_id")
                if not run_id:
                    continue
                row = {
                    "run_id": str(run_id),
                    "graph_id": payload.get("graph_id"),
                    "status": str(payload.get("status") or payload.get("final_status") or "unknown"),
                    "started_at": _as_epoch(payload.get("started_at")),
                    "ended_at": _as_epoch(payload.get("ended_at")) if _as_epoch(payload.get("ended_at")) > 0 else None,
                    "run_dir": str(payload.get("run_dir") or (dag_runs_root / str(run_id))),
                    "correlation_id": payload.get("correlation_id"),
                }
                _add(row)

    rows = list(discovered.values())
    rows.sort(key=lambda r: _as_epoch(r.get("started_at")), reverse=True)
    _DISCOVERY_CACHE["rows"] = rows
    _DISCOVERY_CACHE["limit"] = max(1, limit)
    _DISCOVERY_CACHE["expires_at"] = now + _run_discovery_ttl_seconds()
    return rows[: max(1, limit)]


def init_db():
    with _conn():
        return


def backfill_discovered_runs(limit: int = 5000) -> dict[str, Any]:
    """Persist discovered run rows from disk into the shared runs table. Additive only (INSERT OR REPLACE / merge); never truncates or wipes. DB is primary; disk is backup."""
    init_db()
    cleanup = cleanup_invalid_runs()
    discovered = _discover_run_rows(limit=max(1, limit))
    if not discovered:
        return {"ok": True, "discovered": 0, "inserted": 0, "updated": 0, **cleanup}

    inserted = 0
    updated = 0
    with _conn() as c:
        for row in discovered:
            run_id = str(row.get("run_id") or "").strip()
            if not run_id or not _is_valid_discovered_run(row):
                continue
            existing = c.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if existing is None and row.get("run_dir"):
                existing = c.execute("SELECT * FROM runs WHERE run_dir=? LIMIT 1", (row.get("run_dir"),)).fetchone()
            if existing is None and row.get("correlation_id"):
                existing = c.execute("SELECT * FROM runs WHERE correlation_id=? LIMIT 1", (row.get("correlation_id"),)).fetchone()
            payload = {
                "run_id": run_id,
                "graph_id": row.get("graph_id"),
                "status": row.get("status"),
                "started_at": _as_epoch(row.get("started_at")) or None,
                "ended_at": _as_epoch(row.get("ended_at")) or None,
                "run_dir": row.get("run_dir"),
                "correlation_id": row.get("correlation_id"),
            }
            if existing is None:
                c.execute(
                    """
                    INSERT OR REPLACE INTO runs(run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        payload["run_id"],
                        payload["graph_id"],
                        payload["status"],
                        payload["started_at"],
                        payload["ended_at"],
                        payload["run_dir"],
                        payload["correlation_id"],
                    ),
                )
                inserted += 1
                continue
            merged = _merge_run_rows(dict(existing), payload)
            if Path(str(merged.get("run_dir") or "")).name == run_id and merged.get("run_id") != run_id:
                merged["run_id"] = run_id
            needs_update = merged != dict(existing)
            if needs_update:
                if merged.get("run_id") != dict(existing).get("run_id"):
                    c.execute("DELETE FROM runs WHERE run_id=?", (dict(existing).get("run_id"),))
                c.execute(
                    """
                    INSERT OR REPLACE INTO runs(run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        merged.get("run_id"),
                        merged.get("graph_id"),
                        merged.get("status"),
                        merged.get("started_at"),
                        merged.get("ended_at"),
                        merged.get("run_dir"),
                        merged.get("correlation_id"),
                    ),
                )
                updated += 1
    _DISCOVERY_CACHE.update({"expires_at": 0.0, "limit": 0, "rows": []})
    return {"ok": True, "discovered": len(discovered), "inserted": inserted, "updated": updated, **cleanup}


def upsert_run(run: dict):
    init_db()
    started = _as_epoch(run.get("started_at"))
    ended = _as_epoch(run.get("ended_at"))
    with _conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO runs(run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id, blocked_reason, pending_request_json)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                run.get("run_id"),
                run.get("graph_id"),
                run.get("status"),
                started if started > 0 else None,
                ended if ended > 0 else None,
                run.get("run_dir"),
                run.get("correlation_id"),
                run.get("blocked_reason"),
                run.get("pending_request_json"),
            ),
        )
    _DISCOVERY_CACHE.update({"expires_at": 0.0, "limit": 0, "rows": []})


def reconcile_runs_from_disk(*, limit: int = 8000, stale_running_minutes: int = 2) -> dict[str, Any]:
    """Backfill disk summaries into DB and repair stale active rows. Returns mismatch stats."""
    init_db()
    import time

    mismatches_before = 0
    with _conn() as c:
        rows = c.execute(
            f"""
            SELECT run_id, status, run_dir FROM runs
            WHERE COALESCE(run_dir, '') != ''
              AND status IN ({",".join("?" for _ in _ACTIVE_RUN_STATUSES + ("failed",))})
            """,
            _ACTIVE_RUN_STATUSES + ("failed",),
        ).fetchall()
    for row in rows:
        data = _row_to_dict(row)
        run_dir = Path(str(data.get("run_dir") or ""))
        if not run_dir.exists():
            continue
        inferred = _infer_run_from_dir(run_dir)
        disk_status = str(inferred.get("status") or "").strip().lower()
        db_status = str(data.get("status") or "").strip().lower()
        if disk_status and db_status and disk_status != db_status:
            mismatches_before += 1

    backfill = backfill_discovered_runs(limit=max(500, limit))

    repaired = 0
    cutoff = time.time() - (max(0, int(stale_running_minutes)) * 60)
    with _conn() as c:
        running_rows = c.execute(
            f"""
            SELECT run_id, run_dir, started_at FROM runs
            WHERE status IN ({",".join("?" for _ in _ACTIVE_RUN_STATUSES)})
              AND COALESCE(run_dir, '') != ''
            """,
            _ACTIVE_RUN_STATUSES,
        ).fetchall()
    for row in running_rows:
        data = _row_to_dict(row)
        run_dir = Path(str(data.get("run_dir") or ""))
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue
        started_ts = _as_epoch(data.get("started_at"))
        if started_ts > cutoff and started_ts > 0:
            continue
        inferred = _infer_run_from_dir(run_dir)
        disk_status = str(inferred.get("status") or "").strip().lower()
        if disk_status in _TERMINAL_RUN_STATUSES:
            upsert_run(inferred)
            repaired += 1

    return {
        "ok": True,
        "mismatches_before": mismatches_before,
        "repaired_stale_running": repaired,
        **backfill,
    }


def list_runs(limit: int = 200):
    """List runs from the shared gateway DB (primary). If DB has no runs, backfill once from disk then return."""
    init_db()
    cleanup_invalid_runs()
    with _conn() as c:
        rows = c.execute("SELECT * FROM runs").fetchall()
        indexed = [_row_to_dict(r) for r in rows if _is_valid_discovered_run(_row_to_dict(r))]
    if not indexed:
        backfill_discovered_runs(limit=max(500, limit * 10))
        with _conn() as c:
            rows = c.execute("SELECT * FROM runs").fetchall()
            indexed = [_row_to_dict(r) for r in rows if _is_valid_discovered_run(_row_to_dict(r))]
    indexed.sort(
        key=lambda r: (
            1 if _is_gate_queue_stub(r) else 0,
            -(_as_epoch(r.get("started_at")) or 0),
        ),
    )
    return indexed[: max(1, limit)]


def get_run(run_id: str):
    """Get run from DB only. If not in DB, optionally read from disk (read-only, no write)."""
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if row:
        return _row_to_dict(row)
    for discovered in _discover_run_rows(limit=5000):
        if str(discovered.get("run_id")) == run_id:
            return discovered
        run_dir = discovered.get("run_dir") or ""
        if run_dir and (run_dir.rstrip("/").endswith("/" + run_id) or Path(run_dir).name == run_id):
            return discovered
    return None


def set_status(run_id: str, status: str, blocked_reason: str | None = None):
    init_db()
    with _conn() as c:
        if blocked_reason is not None and status == "blocked":
            c.execute(
                "UPDATE runs SET status=?, blocked_reason=? WHERE run_id=?",
                (status, blocked_reason, run_id),
            )
        else:
            c.execute("UPDATE runs SET status=? WHERE run_id=?", (status, run_id))
    _DISCOVERY_CACHE.update({"expires_at": 0.0, "limit": 0, "rows": []})
