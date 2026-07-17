"""
Tool outcome logging: record success/fail/timeout/partial with latency, error_class, artifact links; emit TOOL_OUTCOME_RECORDED.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_rationale


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_tool_outcome(
    *,
    tool_call_id: str,
    tool_name: str,
    inputs_hash: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    outcome: str,
    latency_ms: int,
    error_class: Optional[str] = None,
    cost_units: Optional[float] = None,
    artifact_links: Optional[List[str]] = None,
    summary: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Optionally write summary artifact; emit TOOL_OUTCOME_RECORDED.
    outcome must be one of: success, fail, timeout, partial.
    Returns record id (event object id).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    rec_id = hashlib.sha256(f"{tool_call_id}:{ts}".encode()).hexdigest()
    links = list(artifact_links or [])
    if summary is not None:
        write_rationale(workspace_root, rec_id, {**summary, "tool_call_id": tool_call_id, "tool_name": tool_name, "ts": ts}, subdir="tool_outcome")
        links.insert(0, rec_id)
    if outcome not in ("success", "fail", "timeout", "partial"):
        outcome = "fail"
    emit(
        "TOOL_OUTCOME_RECORDED",
        "tool_outcome",
        rec_id,
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "inputs_hash": inputs_hash,
            "outcome": outcome,
            "error_class": (error_class or ""),
            "latency_ms": int(latency_ms),
            "cost_units": float(cost_units) if cost_units is not None else 0.0,
            "artifact_links": links,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return rec_id
