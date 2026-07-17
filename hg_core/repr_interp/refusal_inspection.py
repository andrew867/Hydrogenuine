"""
Layer 8 Phase 5: Refusal-inspection — record refusal reason as inspection result when a component refuses.
Opt-in; triggered on GATE_DENIED / APPROVAL_REQUESTED (executor) or similar refusal paths.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REFUSAL_PROMPT_ID = "refusal_reason"


def is_refusal_inspection_enabled(
    workspace_root: Optional[Path] = None,
    run_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Return True if refusal-inspection is enabled via env or run_config."""
    if run_config is not None and run_config.get("repr_interp_refusal_inspection") is True:
        return True
    return os.environ.get("REPR_INTERP_REFUSAL_INSPECTION", "").strip().lower() in ("1", "true", "yes")


def record_refusal_inspection(
    workspace_root: Path,
    refusal_reason: str,
    event_id: Optional[str] = None,
    run_id: Optional[str] = None,
    node_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    run_dir: Optional[Path] = None,
    context_ref: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Record a refusal as an inspection result (prompt_id=refusal_reason).
    Uses refusal_reason as proxy output_text when no live Patchscopes run is performed.
    Stores via store_inspection_result; links to event_id, run_id, node_id, decision_id.
    Returns the stored result record or None if storage fails.
    """
    workspace_root = Path(workspace_root)
    request_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result: Dict[str, Any] = {
        "prompt_id": REFUSAL_PROMPT_ID,
        "request_id": request_id,
        "inspection_id": request_id,
        "output_text": refusal_reason or "(no reason provided)",
        "ts": ts,
        "created_at": ts,
    }
    if event_id is not None:
        result["event_id"] = event_id
    if run_id is not None:
        result["run_id"] = run_id
    if node_id is not None:
        result["node_id"] = node_id
    if decision_id is not None:
        result["decision_id"] = decision_id
    if context_ref:
        result["context_ref"] = context_ref
    try:
        from hg_core.repr_interp.storage import store_inspection_result
        store_inspection_result(workspace_root, result, run_dir=run_dir)
        return result
    except Exception:
        return None
