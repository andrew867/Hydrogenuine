"""
Modulation: emit MODULATION_APPLIED with before/after state and rationale ref.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit
from .artifacts import write_modulation_rationale


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def apply_modulation(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    before_state: Dict[str, Any],
    after_state: Dict[str, Any],
    rationale: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Write rationale artifact (if rationale provided), emit MODULATION_APPLIED.
    Returns modulation_id (event object id).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    mod_id = hashlib.sha256(f"{ts}:{before_state!r}:{after_state!r}".encode()).hexdigest()
    rationale_artifact_id = mod_id
    if rationale:
        write_modulation_rationale(
            workspace_root,
            mod_id,
            {"modulation_id": mod_id, "ts": ts, "before_state": before_state, "after_state": after_state, "rationale": rationale},
        )
    emit(
        "MODULATION_APPLIED",
        "modulation",
        mod_id,
        {
            "modulation_id": mod_id,
            "ts": ts,
            "before_state": before_state,
            "after_state": after_state,
            "rationale_artifact_id": rationale_artifact_id,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return mod_id
