"""
Metacognition artifact storage: rationale, tool outcome summaries, capability profiles, postmortems.
Writes under artifacts/metacognition/; returns path/artifact_id for ledger references.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_gateway.artifact_registry import upsert_reflection_artifact
from hg_gateway.db import get_connection

try:
    import yaml
except ImportError:
    yaml = None


def _metacognition_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "metacognition"


def _date_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def write_rationale(workspace_root: Path, artifact_id: str, obj: Dict[str, Any], subdir: str = "rationale") -> Dict[str, Any]:
    """Write JSON to artifacts/metacognition/<subdir>/<date>/<artifact_id>.json. Returns {path, artifact_id}."""
    root = _metacognition_root(workspace_root) / subdir / _date_prefix()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{artifact_id}.json"
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw)
    return {"path": str(path), "artifact_id": artifact_id}


def write_capability_profile(workspace_root: Path, agent_key_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Write capability profile YAML to artifacts/capabilities/<agent_key_id>/capability_profile.yaml."""
    root = Path(workspace_root) / "artifacts" / "capabilities" / agent_key_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / "capability_profile.yaml"
    if yaml is None:
        path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    else:
        path.write_text(yaml.dump(profile, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    artifact_id = f"cap_{agent_key_id}_{_date_prefix()}"
    return {"path": str(path), "artifact_id": artifact_id}


def write_postmortem_artifact(workspace_root: Path, postmortem_id: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    """Write postmortem JSON to artifacts/metacognition/postmortems/<date>/<postmortem_id>.json."""
    return write_rationale(workspace_root, postmortem_id, obj, subdir="postmortems")


def write_reflection_artifact(
    workspace_root: Path,
    artifact_id: str,
    obj: Dict[str, Any],
    *,
    source_event_ids: list[str] | None = None,
    source_memory_ids: list[str] | None = None,
    source_links: list[Dict[str, Any]] | None = None,
    confidence: float = 0.0,
    verification_status: str = "provisional",
    reviewed_by: str | None = None,
    promoted_at: str | None = None,
    title: str | None = None,
    change_summary: str | None = None,
) -> Dict[str, Any]:
    """Store a typed reflection artifact in the gateway artifact registry."""
    gateway_db = Path(workspace_root) / "memory" / "gateway.sqlite3"
    reflection_title = title or str(obj.get("title") or obj.get("summary") or artifact_id)
    summary = str(obj.get("summary") or obj.get("title") or reflection_title)
    event_ids = source_event_ids if source_event_ids is not None else list(obj.get("source_event_ids") or [])
    memory_ids = source_memory_ids if source_memory_ids is not None else list(obj.get("source_memory_ids") or [])
    links = source_links if source_links is not None else list(obj.get("source_links") or [])
    with get_connection(str(gateway_db)) as conn:
        return upsert_reflection_artifact(
            conn,
            artifact_id=artifact_id,
            title=reflection_title,
            summary=summary,
            findings_json=obj,
            source_event_ids=event_ids,
            source_memory_ids=memory_ids,
            source_links=links,
            confidence=confidence,
            verification_status=verification_status,
            reviewed_by=reviewed_by,
            promoted_at=promoted_at,
            actor_id="system",
            change_summary=change_summary or "stored reflection artifact",
        )
