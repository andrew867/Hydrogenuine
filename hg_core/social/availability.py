"""Availability: AVAILABILITY_DECLARED with windows and rationale."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_availability_rationale


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def declare_availability(
    *,
    agent_id: str,
    windows: List[Dict[str, Any]],
    timezone: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    notes: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit AVAILABILITY_DECLARED. windows: [{start_ts, end_ts, status: available|unavailable|oncall}]. Returns record id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    rec_id = hashlib.sha256(f"{agent_id}:{ts}".encode()).hexdigest()
    rationale_artifact_id = rec_id
    if notes:
        write_availability_rationale(workspace_root, rec_id, {"agent_id": agent_id, "notes": notes, "ts": ts})
    emit(
        "AVAILABILITY_DECLARED",
        "availability",
        rec_id,
        {"agent_id": agent_id, "windows": windows, "timezone": timezone, "ts": ts, "rationale_artifact_id": rationale_artifact_id},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return rec_id
