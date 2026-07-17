"""
Audit: emit PRIVILEGED_ACCESS or AUDIT_EVENT for sensitive views, export, overrides, policy publish.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def emit_audit_event(
    *,
    action: str,
    resource: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit PRIVILEGED_ACCESS for audit trail (sensitive view, export, override, policy). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    import hashlib
    import time
    obj_id = "aud_" + hashlib.sha256(f"{action}:{resource}:{time.time()}".encode()).hexdigest()[:16]
    payload = {"action": action, "resource": resource}
    if rationale_artifact_id:
        payload["rationale_artifact_id"] = rationale_artifact_id
    if details:
        payload["details"] = details
    return emit(
        "PRIVILEGED_ACCESS",
        "audit",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
