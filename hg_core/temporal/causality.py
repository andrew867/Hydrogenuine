"""
Causal links: cause_refs -> effect_refs with strength, type, status; CAUSAL_LINK_RECORDED.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_causal_mechanism


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_causal_link(
    *,
    cause_refs: List[Dict[str, Any]],
    effect_refs: List[Dict[str, Any]],
    strength: float,
    link_type: str,
    status: str,
    mechanism_artifact_id: Optional[str] = None,
    mechanism_notes: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Write mechanism artifact (if mechanism_notes provided), emit CAUSAL_LINK_RECORDED.
    link_type: direct|contributing|blocked; status: hypothesized|supported|confirmed.
    Returns link_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    link_id = hashlib.sha256(f"{ts}:{cause_refs!r}:{effect_refs!r}".encode()).hexdigest()
    if link_type not in ("direct", "contributing", "blocked"):
        link_type = "contributing"
    if status not in ("hypothesized", "supported", "confirmed"):
        status = "hypothesized"
    art_id = mechanism_artifact_id or link_id
    if mechanism_notes is not None:
        mech = {"link_id": link_id, "ts": ts, "mechanism_notes": mechanism_notes, "cause_refs": cause_refs, "effect_refs": effect_refs}
        out = write_causal_mechanism(workspace_root, link_id, mech)
        art_id = out["artifact_id"]
    emit(
        "CAUSAL_LINK_RECORDED",
        "causal_link",
        link_id,
        {
            "link_id": link_id,
            "cause_refs": cause_refs,
            "effect_refs": effect_refs,
            "strength": max(0.0, min(1.0, strength)),
            "type": link_type,
            "status": status,
            "mechanism_artifact_id": art_id,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return link_id
