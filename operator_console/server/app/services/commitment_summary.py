from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_gateway.commitment_ledger import list_commitments, summarize_commitments


def _binding_agent_id(binding: dict[str, Any] | None) -> str | None:
    if not isinstance(binding, dict):
        return None
    value = str(binding.get("operational_agent_id") or "").strip()
    return value or None


def _binding_entity_id(binding: dict[str, Any] | None, task_name: str | None = None) -> str | None:
    if isinstance(binding, dict):
        value = str(binding.get("operational_session_target") or "").strip()
        if value:
            return value
    value = str(task_name or "").strip()
    return value or None


def build_commitment_summary(
    *,
    root: Path | None,
    task_name: str,
    session_target: str,
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if root is None:
        return {
            "status": "none",
            "count": 0,
            "open_count": 0,
            "fulfilled_count": 0,
            "expired_count": 0,
            "overdue_count": 0,
            "recent_commitments": [],
            "next_due_at": None,
            "latest_commitment": None,
            "required_actions": [],
        }
    agent_id = _binding_agent_id(binding)
    entity_id = _binding_entity_id(binding, task_name)
    commitments = list_commitments(
        root,
        task_name=task_name,
        operational_agent_id=agent_id,
        entity_id=entity_id,
        limit=20,
    )
    summary = summarize_commitments(commitments)
    open_count = int(summary.get("open_count") or 0)
    overdue_count = int(summary.get("overdue_count") or 0)
    required_actions: list[str] = []
    if overdue_count:
        required_actions.append("resolve_overdue_commitments")
    elif open_count:
        required_actions.append("track_open_commitments")
    latest = summary.get("latest_commitment") if isinstance(summary.get("latest_commitment"), dict) else {}
    next_due_at = None
    due_values = [
        str(item.get("due_at") or "").strip()
        for item in commitments
        if isinstance(item, dict) and str(item.get("status") or "").strip() not in {"fulfilled", "expired"} and str(item.get("due_at") or "").strip()
    ]
    if due_values:
        next_due_at = sorted(due_values)[0]
    return {
        **summary,
        "task_name": task_name,
        "session_target": session_target,
        "operational_agent_id": agent_id,
        "entity_id": entity_id,
        "next_due_at": next_due_at,
        "latest_commitment": latest or None,
        "required_actions": required_actions,
    }
