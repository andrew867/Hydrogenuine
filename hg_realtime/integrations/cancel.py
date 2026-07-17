"""Cancel a running DAG run: stop heartbeat, kill process, release lease, update run index."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from ..leases.store import RunLeaseStore
from .run_tracker import get_default_tracker

logger = logging.getLogger(__name__)


def cancel_run(
    run_id: str,
    lease_store: RunLeaseStore,
    *,
    set_status: Optional[Callable[[str, str], None]] = None,
    terminate_timeout_s: float = 5.0,
) -> dict:
    """
    Mark run cancelled: stop heartbeat, terminate process, release lease, set run index status.
    set_status(run_id, status) is called with "cancelled" if provided (e.g. operator_console run_index_db.set_status).
    Returns {"ok": True, "run_id": run_id, "status": "cancelled"} or {"ok": False, "error": "..."}.
    """
    tracker = get_default_tracker()
    try:
        cancelled = tracker.cancel(run_id, lease_store, terminate_timeout_s=terminate_timeout_s, kill_fallback=True)
        if set_status:
            try:
                set_status(run_id, "cancelled")
            except Exception as e:
                logger.warning("set_status failed for run_id=%s: %s", run_id, e)
        if not cancelled:
            lease_store.release(run_id)
        return {"ok": True, "run_id": run_id, "status": "cancelled"}
    except Exception as e:
        logger.exception("cancel_run run_id=%s: %s", run_id, e)
        lease_store.release(run_id)
        if set_status:
            try:
                set_status(run_id, "cancelled")
            except Exception:
                pass
        return {"ok": False, "run_id": run_id, "error": str(e)}
