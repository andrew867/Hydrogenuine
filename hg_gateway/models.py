"""
Shared data models for gateway store (chats, messages, agents, approvals).
Used by both in-memory and SQLite store implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ChatRow:
    chat_id: str
    title: str
    updated_at: str
    unread_count: int = 0
    tenant_id: str = "default"
    fingerprint_id: Optional[str] = None
    skin_id: Optional[str] = None
    swarm_run_id: Optional[str] = None
    swarm_role: Optional[str] = None  # e.g. "entity" | "orchestrator"


@dataclass
class MessageRow:
    message_id: str
    chat_id: str
    role: str
    created_at: str
    content: str
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_payload: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    approvals_required: Optional[bool] = None


# Lifecycle state for Pack 10 drift/quarantine: active, paused, quarantined
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_PAUSED = "paused"
LIFECYCLE_QUARANTINED = "quarantined"


@dataclass
class AgentRow:
    agent_id: str
    label: str
    status: str  # idle, working, blocked, error
    parent_agent_id: Optional[str] = None
    lifecycle_state: str = LIFECYCLE_ACTIVE
    state_reason: Optional[str] = None
    state_updated_at: Optional[str] = None
    state_updated_by: Optional[str] = None


@dataclass
class ApprovalRow:
    id: str
    created_at: str
    resolved_at: Optional[str]
    status: str  # pending, approved, denied
    kind: str
    title: str
    summary: str
    risk: str
    requested_by: str
    payload: Dict[str, Any]
    resolution_note: Optional[str] = None
    assigned_principal_id: Optional[str] = None  # Pack2-08: resolved from escalation chain
    tenant_id: str = "default"  # Pack3: multi-tenant boundaries
