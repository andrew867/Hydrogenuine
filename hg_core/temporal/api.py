"""
Temporal API: episodes, timeline, belief snapshot, causal links, branches, audit export.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .belief_snapshots import build_belief_snapshot


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def list_episodes(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List episodes from materialized index."""
    workspace_root = Path(workspace_root)
    rows = _load_jsonl(_materialized_root(workspace_root) / "episodes.jsonl")
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    return rows[offset : offset + limit]


def get_episode(workspace_root: Path, episode_id: str) -> Optional[Dict[str, Any]]:
    """Get one episode by episode_id."""
    workspace_root = Path(workspace_root)
    for r in _load_jsonl(_materialized_root(workspace_root) / "episodes.jsonl"):
        if r.get("episode_id") == episode_id:
            return r
    return None


def get_timeline(
    workspace_root: Path,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Return ordered timeline events for scope and optional time range."""
    workspace_root = Path(workspace_root)
    rows = _load_jsonl(_materialized_root(workspace_root) / "timeline.jsonl")
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    if start_ts is not None:
        rows = [r for r in rows if (r.get("ts") or "") >= start_ts]
    if end_ts is not None:
        rows = [r for r in rows if (r.get("ts") or "") <= end_ts]
    rows.sort(key=lambda r: r.get("ts", ""))
    return rows[:limit]


def get_belief_snapshot_at(
    workspace_root: Path,
    scope_type: str,
    scope_id: str,
    at_ts: str,
) -> Dict[str, Any]:
    """Return belief snapshot at at_ts (from ledger prefix)."""
    return build_belief_snapshot(Path(workspace_root), scope_type, scope_id, at_ts)


def list_causal_links(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List causal links from materialized index."""
    workspace_root = Path(workspace_root)
    rows = _load_jsonl(_materialized_root(workspace_root) / "causal_links.jsonl")
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    if status is not None:
        rows = [r for r in rows if r.get("status") == status]
    return rows[:limit]


def list_branches(
    workspace_root: Path,
    *,
    decision_id: Optional[str] = None,
    scope_type: Optional[str] = None,
    closed: Optional[bool] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List branches from materialized index; optionally filter by decision_id or closed."""
    workspace_root = Path(workspace_root)
    rows = _load_jsonl(_materialized_root(workspace_root) / "branches.jsonl")
    if decision_id is not None:
        rows = [r for r in rows if r.get("decision_id") == decision_id]
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if closed is not None:
        rows = [r for r in rows if r.get("closed") == closed]
    return rows[:limit]


def export_temporal_audit(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build audit bundle (timeline events, episode refs, snapshot refs), write artifact, emit TEMPORAL_AUDIT_EXPORTED.
    Returns {artifact_path, event_id, bundle_summary}.
    """
    workspace_root = Path(workspace_root)
    timeline_events = get_timeline(workspace_root, scope_type=scope_type, scope_id=scope_id, start_ts=start_ts, end_ts=end_ts, limit=10000)
    episodes_list = list_episodes(workspace_root, scope_type=scope_type, scope_id=scope_id, limit=1000)
    causal_list = list_causal_links(workspace_root, scope_type=scope_type, scope_id=scope_id, limit=1000)
    branches_list = list_branches(workspace_root, scope_type=scope_type, limit=1000)
    event_ids = [e.get("event_id") for e in timeline_events if e.get("event_id")]
    bundle = {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "event_count": len(timeline_events),
        "event_ids": event_ids,
        "episode_count": len(episodes_list),
        "causal_link_count": len(causal_list),
        "branch_count": len(branches_list),
        "timeline_sample": timeline_events[:100],
        "episodes": episodes_list,
    }
    from datetime import datetime, timezone
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    audit_dir = workspace_root / "artifacts" / "temporal" / "audit" / date_prefix
    audit_dir.mkdir(parents=True, exist_ok=True)
    bundle_id = hashlib.sha256(f"{scope_type}:{scope_id}:{date_prefix}:{len(event_ids)}".encode()).hexdigest()[:16]
    artifact_path = audit_dir / f"temporal_audit_{bundle_id}.json"
    artifact_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    scope = scope or {"type": scope_type or "global", "id": scope_id or "default"}
    actor = actor or {"agent_id": "operator", "pubkey": "", "key_id": ""}
    event_id = emit(
        "TEMPORAL_AUDIT_EXPORTED",
        "temporal_audit",
        bundle_id,
        {"artifact_path": str(artifact_path), "event_count": len(event_ids), "scope_type": scope_type, "scope_id": scope_id},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
        object_path=str(artifact_path),
    )
    return {"artifact_path": str(artifact_path), "event_id": event_id, "bundle_summary": {"event_count": len(event_ids), "episode_count": len(episodes_list)}}
