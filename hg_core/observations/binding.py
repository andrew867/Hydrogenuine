"""
Observation binding: emit OBSERVATION_BOUND to link observation to entity/claim.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def emit_observation_bound(
    observation_id: str,
    entity_id: Optional[str] = None,
    claim_id: Optional[str] = None,
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    field_path: Optional[str] = None,
    confidence: float = 1.0,
    method: str = "rule",
    rationale_artifact_id: Optional[str] = None,
) -> str:
    """
    Emit OBSERVATION_BOUND. Returns event_id.
    """
    payload: Dict[str, Any] = {
        "observation_id": observation_id,
        "confidence": confidence,
        "method": method,
    }
    if entity_id:
        payload["entity_id"] = entity_id
    if claim_id:
        payload["claim_id"] = claim_id
    if field_path:
        payload["field_path"] = field_path
    if rationale_artifact_id:
        payload["rationale_artifact_id"] = rationale_artifact_id
    binding_id = f"bound_{observation_id}_{entity_id or ''}_{claim_id or ''}"[:64]
    return emit(
        "OBSERVATION_BOUND",
        "binding",
        binding_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
