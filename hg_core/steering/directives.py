"""
Control Surface Pack 7: Steering directives lifecycle — artifact-backed, publish/apply/supersede, events.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _directives_artifact_root(workspace_root: Path) -> Path:
    return workspace_root / "artifacts" / "steering" / "directives"


def _materialized_root(workspace_root: Path) -> Path:
    return workspace_root / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def publish_directive(
    *,
    target_ref: Dict[str, Any],
    goal: str,
    constraints: List[str],
    autonomy_preset: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: str = "",
    value_profiles: Optional[List[str]] = None,
    continuity_contract_id: Optional[str] = None,
    expires_hours: int = 24 * 7,
    supersedes: Optional[str] = None,
    version: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Create directive artifact and emit STEERING_DIRECTIVE_PUBLISHED.
    Returns directive_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    directive_id = "dir_" + hashlib.sha256(
        f"{target_ref.get('id','')}:{ts}:{goal[:50]}".encode()
    ).hexdigest()[:16]
    expiry_ts = (
        datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    ).isoformat().replace("+00:00", "Z")
    root = _directives_artifact_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    doc: Dict[str, Any] = {
        "directive_id": directive_id,
        "target_ref": target_ref,
        "goal": goal,
        "constraints": constraints,
        "autonomy_preset": autonomy_preset,
        "issued_ts": ts,
        "expires_ts": expiry_ts,
        "rationale_artifact_id": rationale_artifact_id or "",
        "version": version or "1",
        "supersedes": supersedes or "",
    }
    if value_profiles:
        doc["value_profiles"] = value_profiles
    if continuity_contract_id:
        doc["continuity_contract_id"] = continuity_contract_id
    path = root / f"{directive_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    payload = {
        "directive_id": directive_id,
        "target_ref": target_ref,
        "goal": goal,
        "constraints": constraints,
        "autonomy_preset": autonomy_preset,
        "issued_ts": ts,
        "expires_ts": expiry_ts,
        "rationale_artifact_id": rationale_artifact_id or "",
        "version": doc["version"],
        "artifact_path": str(path),
    }
    if supersedes:
        payload["supersedes"] = supersedes
    emit(
        "STEERING_DIRECTIVE_PUBLISHED",
        "steering_directive",
        directive_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return directive_id


def apply_directive(
    *,
    directive_id: str,
    target_ref: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit STEERING_DIRECTIVE_APPLIED (audited). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "STEERING_DIRECTIVE_APPLIED",
        "steering_directive",
        directive_id,
        {"directive_id": directive_id, "target_ref": target_ref, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def supersede_directive(
    *,
    directive_id: str,
    superseded_by_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit STEERING_DIRECTIVE_SUPERSEDED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "STEERING_DIRECTIVE_SUPERSEDED",
        "steering_directive",
        directive_id,
        {
            "directive_id": directive_id,
            "superseded_by": superseded_by_id,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def resolve_directive(workspace_root: Path, directive_id: str) -> Optional[Dict[str, Any]]:
    """Load directive from artifacts/steering/directives/{directive_id}.json."""
    path = _directives_artifact_root(workspace_root) / f"{directive_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_directives(
    workspace_root: Path,
    target_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List directives from materialized steering_directives.jsonl, optional filter by target."""
    root = _materialized_root(workspace_root)
    path = root / "steering_directives.jsonl"
    rows = _load_jsonl(path)
    if target_id:
        rows = [
            r
            for r in rows
            if (r.get("target_ref") or {}).get("id") == target_id
        ]
    rows.sort(key=lambda r: r.get("issued_ts", ""), reverse=True)
    return rows[:limit]


def get_active_directive(
    workspace_root: Path,
    target_id: str,
) -> Optional[Dict[str, Any]]:
    """Return active (latest applied, non-expired) directive for target from materialized state."""
    root = _materialized_root(workspace_root)
    path = root / "steering_active.jsonl"
    for line in _load_jsonl(path):
        if (line.get("target_ref") or {}).get("id") == target_id:
            return line
    return None


def get_steering_timeline(
    workspace_root: Path,
    target_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Steering history for target (published/applied/superseded/expired) from materialized timeline."""
    root = _materialized_root(workspace_root)
    path = root / "steering_timeline.jsonl"
    rows = []
    for r in _load_jsonl(path):
        tr = r.get("target_ref") or (r.get("payload") or {}).get("target_ref")
        if tr and (tr.get("id") == target_id):
            rows.append(r)
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]
