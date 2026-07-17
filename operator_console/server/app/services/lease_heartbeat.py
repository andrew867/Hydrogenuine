"""L10: Run lease heartbeat for POST /runs/{run_id}/heartbeat. Phase 8."""

from __future__ import annotations

import os
from typing import Any, Dict

from ..core.config import settings


def run_heartbeat(run_id: str, lease_id: str, worker_id: str, seq: int) -> Dict[str, Any]:
    """Call RunLeaseStore.heartbeat. Returns { ok } or { ok: False, error }."""
    try:
        from hg_realtime.leases.store import default_lease_store
    except ImportError as e:
        return {"ok": False, "error": str(e)}
    try:
        store = default_lease_store()
        store.heartbeat(run_id=run_id, lease_id=lease_id, worker_id=worker_id, seq=seq)
        return {"ok": True}
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
