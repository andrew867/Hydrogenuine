"""
Capability profile: versioned artifact per agent key; emit CAPABILITY_PROFILE_PUBLISHED.
Profile includes tools (allowed/denied, constraints, expected latency, expected failure rate).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_capability_profile


def publish_capability_profile(
    *,
    agent_key_id: str,
    profile: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Write capability_profile.yaml to artifacts/capabilities/<agent_key_id>/ and emit CAPABILITY_PROFILE_PUBLISHED.
    profile should include: tools (list with name, allowed, constraints?, expected_latency_ms?, expected_failure_rate?), last_updated.
    Returns artifact_id from write.
    """
    workspace_root = Path(workspace_root or ".")
    out = write_capability_profile(workspace_root, agent_key_id, profile)
    artifact_id = out["artifact_id"]
    path = out["path"]
    emit(
        "CAPABILITY_PROFILE_PUBLISHED",
        "capability_profile",
        artifact_id,
        {
            "agent_key_id": agent_key_id,
            "artifact_path": path,
            "artifact_id": artifact_id,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
        object_path=path,
    )
    return artifact_id
