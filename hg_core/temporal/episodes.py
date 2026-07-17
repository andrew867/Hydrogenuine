"""
Episodes: bounded intervals (run/session/cycle); EPISODE_STARTED, EPISODE_ENDED, EPISODE_SUMMARY_PUBLISHED.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_episode_summary


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def start_episode(
    *,
    name: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    participants: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit EPISODE_STARTED. Returns episode_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    scope_type = scope.get("type", "run")
    scope_id = scope.get("id", "default")
    episode_id = hashlib.sha256(f"{scope_type}:{scope_id}:{name}:{ts}".encode()).hexdigest()
    emit(
        "EPISODE_STARTED",
        "episode",
        episode_id,
        {
            "episode_id": episode_id,
            "name": name,
            "start_ts": ts,
            "scope": scope,
            "participants": participants or [],
            "tags": tags or [],
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return episode_id


def end_episode(
    *,
    episode_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    summary: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> None:
    """Optionally publish summary artifact and EPISODE_SUMMARY_PUBLISHED; then emit EPISODE_ENDED."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    summary_artifact_id = ""
    if summary is not None:
        out = write_episode_summary(workspace_root, episode_id, summary)
        summary_artifact_id = out["artifact_id"]
        emit(
            "EPISODE_SUMMARY_PUBLISHED",
            "episode_summary",
            episode_id,
            {"episode_id": episode_id, "summary_artifact_id": summary_artifact_id, "ts": ts},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
            object_path=out["path"],
        )
    emit(
        "EPISODE_ENDED",
        "episode",
        episode_id,
        {"episode_id": episode_id, "end_ts": ts, "summary_artifact_id": summary_artifact_id},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
