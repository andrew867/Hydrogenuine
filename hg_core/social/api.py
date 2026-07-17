"""Social API: handoffs, availability, beliefs, exposures, escalations, conflicts, misalignments."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def list_handoffs(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    from_agent_id: Optional[str] = None,
    to_agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = _load_jsonl(_materialized_root(workspace_root) / "handoffs.jsonl")
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    if from_agent_id is not None:
        rows = [r for r in rows if r.get("from_agent_id") == from_agent_id]
    if to_agent_id is not None:
        rows = [r for r in rows if r.get("to_agent_id") == to_agent_id]
    if status is not None:
        rows = [r for r in rows if r.get("status") == status]
    return rows[:limit]


def list_availability(
    workspace_root: Path,
    *,
    agent_id: Optional[str] = None,
    scope_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = _load_jsonl(_materialized_root(workspace_root) / "availability.jsonl")
    if agent_id is not None:
        rows = [r for r in rows if r.get("agent_id") == agent_id]
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    return rows[:limit]


def list_beliefs(
    workspace_root: Path,
    *,
    subject_agent_id: Optional[str] = None,
    claim_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    scope_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = _load_jsonl(_materialized_root(workspace_root) / "beliefs.jsonl")
    if subject_agent_id is not None:
        rows = [r for r in rows if r.get("subject_agent_id") == subject_agent_id]
    if claim_id is not None:
        rows = [r for r in rows if r.get("claim_id") == claim_id]
    if entity_id is not None:
        rows = [r for r in rows if r.get("entity_id") == entity_id]
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope", {}).get("type") == scope_type]
    return rows[:limit]


def list_exposures(
    workspace_root: Path,
    *,
    agent_id: Optional[str] = None,
    ref_id: Optional[str] = None,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = _load_jsonl(_materialized_root(workspace_root) / "exposures.jsonl")
    if agent_id is not None:
        rows = [r for r in rows if r.get("agent_id") == agent_id]
    if ref_id is not None:
        rows = [r for r in rows if r.get("ref_id") == ref_id]
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if scope_id is not None:
        rows = [r for r in rows if r.get("scope_id") == scope_id]
    return rows[:limit]


def list_escalations(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    handoff_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = _load_jsonl(_materialized_root(workspace_root) / "escalations.jsonl")
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if handoff_id is not None:
        rows = [r for r in rows if r.get("handoff_id") == handoff_id]
    return rows[:limit]


def list_conflicts(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = _load_jsonl(_materialized_root(workspace_root) / "conflicts.jsonl")
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    return rows[:limit]


def list_misalignments(
    workspace_root: Path,
    *,
    scope_type: Optional[str] = None,
    agent_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = _load_jsonl(_materialized_root(workspace_root) / "misalignments.jsonl")
    if scope_type is not None:
        rows = [r for r in rows if r.get("scope_type") == scope_type]
    if agent_id is not None:
        rows = [r for r in rows if r.get("agent_id") == agent_id]
    if decision_id is not None:
        rows = [r for r in rows if r.get("decision_id") == decision_id]
    return rows[:limit]
