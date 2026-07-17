"""L10 run request: DagLauncher.launch for POST /runs/request. Phase 8."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

from ..core.config import settings


def _run_request(
    workflow_id: str,
    tenant_id: str = "default",
    actor_id: str = "api",
    correlation_id: Optional[str] = None,
    resolved_inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Launch a DAG run via DagLauncher. Returns { ok, run_id } or { ok: False, error }."""
    try:
        from hg_realtime.integrations.dag_launcher import DagLauncher
        from hg_realtime.integrations.run_index import default_run_index_writer
        from hg_realtime.leases.store import default_lease_store
        from hg_realtime.scheduler.models import RunRequested
    except ImportError as e:
        return {"ok": False, "error": f"launcher unavailable: {e}"}

    correlation_id = correlation_id or str(uuid.uuid4())
    resolved_inputs = resolved_inputs if isinstance(resolved_inputs, dict) else {}
    req = RunRequested(
        request_id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        resolved_inputs=resolved_inputs,
    )
    run_index = default_run_index_writer()
    lease_store = default_lease_store()
    try:
        launcher = DagLauncher(
            run_index_writer=run_index,
            lease_store=lease_store,
            worker_id="operator_console",
        )
        run_id = launcher.launch(req)
        return {"ok": True, "run_id": run_id, "correlation_id": correlation_id}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
