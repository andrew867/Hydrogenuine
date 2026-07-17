"""
Retention enforcement: expire artifacts by policy, emit TOMBSTONE_RECORDED for ledger references (payload access removed).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def record_tombstone(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    artifact_path: str,
    retention_policy_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit TOMBSTONE_RECORDED when an artifact is redacted/deleted per retention policy. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    import hashlib
    obj_id = "tomb_" + hashlib.sha256(artifact_path.encode()).hexdigest()[:16]
    payload = {"artifact_path": artifact_path}
    if retention_policy_id:
        payload["retention_policy_id"] = retention_policy_id
    return emit(
        "TOMBSTONE_RECORDED",
        "tombstone",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def list_artifacts_for_retention(workspace_root: Path, retention_policy_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List artifact paths that could be subject to retention (from artifacts/ tree). Does not mutate; caller runs record_tombstone after actual removal."""
    root = Path(workspace_root) / "artifacts"
    if not root.exists():
        return []
    out = []
    for f in root.rglob("*"):
        if f.is_file():
            rel = str(f.relative_to(workspace_root))
            out.append({"path": rel, "retention_policy_id": retention_policy_id})
    return out[:1000]
