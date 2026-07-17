"""
Control Surface Pack 1: UI data model — derived views for Swarm Ops Console.
Everything derivable from ledger + materialized views.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class EntityState(TypedDict, total=False):
    id: str
    role: str
    group_id: str
    status: str
    autonomy_level: str
    current_work_item_id: Optional[str]
    current_thread_id: Optional[str]
    last_event_ts: str


class GroupState(TypedDict, total=False):
    id: str
    members: List[str]
    aggregated_gap: Optional[float]
    aggregated_risk: Optional[float]
    incidents_open: int
    safeguards_active: int
    budget_status: str


class ThreadState(TypedDict, total=False):
    thread_id: str
    participants: List[str]
    last_messages: List[Dict[str, Any]]
    attachments_refs: List[str]


class ControlAction(TypedDict, total=False):
    type: str
    target_ref: Dict[str, Any]
    reason_artifact_id: Optional[str]
    expiry: Optional[str]
    required_quorum: Optional[Dict[str, Any]]
