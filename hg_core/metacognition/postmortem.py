"""
Postmortem: record root cause, corrective actions; emit POSTMORTEM_PUBLISHED.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_postmortem_artifact


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_postmortem(
    *,
    related_event_ids: List[str],
    related_decision_ids: List[str],
    root_cause_tags: List[str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    postmortem_artifact_id: Optional[str] = None,
    corrective_action_artifact_ids: Optional[List[str]] = None,
    policy_change_artifact_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
    body: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Write postmortem artifact and emit POSTMORTEM_PUBLISHED.
    Returns postmortem_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    postmortem_id = postmortem_artifact_id or hashlib.sha256(f"{ts}:{','.join(related_decision_ids or [])}".encode()).hexdigest()
    obj = {
        "postmortem_id": postmortem_id,
        "ts": ts,
        "related_event_ids": related_event_ids or [],
        "related_decision_ids": related_decision_ids or [],
        "root_cause_tags": root_cause_tags or [],
        "corrective_action_artifact_ids": corrective_action_artifact_ids or [],
        "policy_change_artifact_id": policy_change_artifact_id,
        **(body or {}),
    }
    write_postmortem_artifact(workspace_root, postmortem_id, obj)
    emit(
        "POSTMORTEM_PUBLISHED",
        "postmortem",
        postmortem_id,
        {
            "postmortem_id": postmortem_id,
            "related_event_ids": related_event_ids or [],
            "related_decision_ids": related_decision_ids or [],
            "postmortem_artifact_id": postmortem_id,
            "corrective_action_artifact_ids": corrective_action_artifact_ids or [],
            "policy_change_artifact_id": policy_change_artifact_id or "",
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return postmortem_id
