"""
Belief attribution: BELIEF_MODEL_UPDATED (with basis_refs), BELIEF_MODEL_OVERRIDDEN (with rationale; never mutates facts).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_belief_override_rationale


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_belief_model_updated(
    *,
    subject_agent_id: str,
    scope: Dict[str, str],
    confidence: float,
    basis_refs: List[Dict[str, Any]],
    claim_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor: Optional[Dict[str, str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit BELIEF_MODEL_UPDATED. basis_refs required (evidence); no basis, no belief. Returns belief_id."""
    workspace_root = Path(workspace_root or ".")
    if not basis_refs:
        raise ValueError("basis_refs required for belief model update")
    ts = _iso_ts()
    belief_id = hashlib.sha256(f"{subject_agent_id}:{claim_id or entity_id}:{ts}".encode()).hexdigest()
    payload: Dict[str, Any] = {
        "belief_id": belief_id,
        "subject_agent_id": subject_agent_id,
        "scope": scope,
        "confidence": max(0.0, min(1.0, confidence)),
        "basis_refs": basis_refs,
        "ts": ts,
    }
    if claim_id:
        payload["claim_id"] = claim_id
    if entity_id:
        payload["entity_id"] = entity_id
    emit(
        "BELIEF_MODEL_UPDATED",
        "belief",
        belief_id,
        payload,
        scope=scope,
        actor=actor or {},
        workspace_root=workspace_root,
    )
    return belief_id


def record_belief_override(
    *,
    subject_agent_id: str,
    scope: Dict[str, str],
    claim_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    rationale: str,
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit BELIEF_MODEL_OVERRIDDEN with rationale artifact. Overrides never mutate facts; they are separate views. Returns override event id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    override_id = hashlib.sha256(f"override:{subject_agent_id}:{claim_id or entity_id}:{ts}".encode()).hexdigest()
    write_belief_override_rationale(
        workspace_root,
        override_id,
        {"subject_agent_id": subject_agent_id, "claim_id": claim_id, "entity_id": entity_id, "rationale": rationale, "ts": ts},
    )
    payload: Dict[str, Any] = {
        "override_id": override_id,
        "subject_agent_id": subject_agent_id,
        "scope": scope,
        "rationale_artifact_id": override_id,
        "ts": ts,
    }
    if claim_id:
        payload["claim_id"] = claim_id
    if entity_id:
        payload["entity_id"] = entity_id
    return emit(
        "BELIEF_MODEL_OVERRIDDEN",
        "belief_override",
        override_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
