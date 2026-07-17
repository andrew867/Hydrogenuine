"""
Backpressure controller: worker health/lag from materializer status; optionally emit MODULATION_APPLIED when lag exceeds threshold.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.extras.rebuild_verify import get_materializer_status
from hg_core.affective import apply_modulation


def check_backpressure(workspace_root: Path) -> Dict[str, Any]:
    """Return worker health summary: materializer status (ok, per-materializer checkpoint/lag)."""
    status = get_materializer_status(Path(workspace_root))
    return {"ok": status.get("ok", True), "materializers": status.get("materializers", {})}


def apply_backpressure_if_needed(
    *,
    workspace_root: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    lag_threshold_scopes: int = 2,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    If materializer status indicates lag (e.g. many scopes behind), emit MODULATION_APPLIED (e.g. tighten gating).
    before_state/after_state: e.g. before_state={"trust_band": 2}, after_state={"trust_band": 1}.
    Returns modulation_id if emitted, else None.
    """
    workspace_root = Path(workspace_root)
    status = get_materializer_status(workspace_root)
    mat = status.get("materializers") or {}
    total_scopes = sum(len(m.get("scopes") or []) for m in mat.values() if isinstance(m, dict) and "scopes" in m)
    if not mat:
        return None
    if before_state is None:
        before_state = {"trust_band": 1}
    if after_state is None:
        after_state = {"trust_band": 0}
    lagged = sum(1 for m in mat.values() if isinstance(m, dict) and m.get("error"))
    if lagged >= lag_threshold_scopes or (lagged > 0 and total_scopes > 0 and lagged / max(1, len(mat)) >= 0.5):
        return apply_modulation(
            scope=scope,
            actor=actor,
            before_state=before_state,
            after_state=after_state,
            rationale="backpressure: materializer lag or errors",
            workspace_root=workspace_root,
        )
    return None
