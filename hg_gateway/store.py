"""
Gateway store: interface and implementations (in-memory, SQLite).

Backend is selected via HG_GATEWAY_STORE=sqlite|postgres|memory (default sqlite).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from hg_gateway.models import LIFECYCLE_ACTIVE, AgentRow, ApprovalRow, ChatRow, MessageRow
from hg_gateway.llm_defaults import get_default_model, get_default_provider

# Re-export for backward compatibility
__all__ = [
    "ChatRow",
    "MessageRow",
    "AgentRow",
    "ApprovalRow",
    "InMemoryStore",
    "get_store",
    "reset_store_for_tests",
    "PostgresStore",
]


def _chat_key(tenant_id: str, chat_id: str) -> tuple:
    return (tenant_id, chat_id)


class InMemoryStore:
    """In-memory store for chats, messages, agents, and approvals. Pack3: all methods take tenant_id first."""

    def __init__(self) -> None:
        self._chats: Dict[tuple, ChatRow] = {}
        self._messages: Dict[tuple, List[MessageRow]] = {}
        self._agents: Dict[tuple, List[AgentRow]] = {}
        self._approvals: Dict[str, ApprovalRow] = {}
        self._lock_approvals: Dict[str, str] = {}
        self._chat_traits: Dict[tuple, Dict[str, float]] = {}  # (tenant_id, chat_id) -> trait path -> value
        self._chat_persona_state: Dict[tuple, Dict[str, Any]] = {}
        self._chat_persona_autonomy_state: Dict[tuple, Dict[str, Any]] = {}
        self._persona_naturalness_turns: Dict[str, Dict[str, Any]] = {}
        self._persona_naturalness_issues: List[Dict[str, Any]] = []
        self._persona_autonomy_turns: Dict[str, Dict[str, Any]] = {}
        # Pack3 Phase 6: prompt and model registry (in-memory)
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}
        self._turn_provenance: Dict[str, Dict[str, Any]] = {}
        _n = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._prompts["default"] = {"id": "default", "tenant_id": "default", "name": "default", "version": "1", "body": "You are a helpful assistant.", "owner": "system", "created_at": _n}
        self._model_configs["default"] = {
            "id": "default",
            "tenant_id": "default",
            "version": "1",
            "model_id": get_default_model(get_default_provider()),
            "params": {"max_tokens": 1024, "temperature": 0.7},
            "created_at": _n,
        }
        # Pack 13: tenant_settings and tenant_domains (in-memory for tests)
        self._tenant_settings: Dict[str, Dict[str, Any]] = {
            "default": {"tenant_id": "default", "display_name": "Default", "status": "active", "logo_artifact_id": None, "theme": {}, "support_links": [], "updated_at": _n},
        }
        self._tenant_domains: Dict[str, str] = {}  # hostname -> tenant_id

    def chat_list(
        self,
        tenant_id: str,
        include_archived: bool = False,
        archived_only: bool = False,
        include_deleted: bool = False,
        deleted_only: bool = False,
    ) -> List[Dict[str, Any]]:
        out = []
        for (tid, cid), c in self._chats.items():
            if tid != tenant_id:
                continue
            row = {
                "chat_id": c.chat_id,
                "title": c.title,
                "updated_at": c.updated_at,
                "unread_count": c.unread_count,
            }
            if getattr(c, "fingerprint_id", None) is not None:
                row["fingerprint_id"] = c.fingerprint_id
            if getattr(c, "skin_id", None) is not None:
                row["skin_id"] = c.skin_id
            if getattr(c, "swarm_run_id", None) is not None:
                row["swarm_run_id"] = c.swarm_run_id
            if getattr(c, "swarm_role", None) is not None:
                row["swarm_role"] = c.swarm_role
            out.append(row)
        out.sort(key=lambda x: x["updated_at"], reverse=True)
        return out

    def chat_create(
        self,
        tenant_id: str,
        title: Optional[str] = None,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        swarm_role: Optional[str] = None,
    ) -> str:
        chat_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        key = _chat_key(tenant_id, chat_id)
        self._chats[key] = ChatRow(
            chat_id=chat_id,
            title=title or "New chat",
            updated_at=now,
            tenant_id=tenant_id,
            fingerprint_id=fingerprint_id,
            skin_id=skin_id,
            swarm_run_id=swarm_run_id,
            swarm_role=swarm_role,
        )
        self._messages[key] = []
        self._agents[key] = []
        return chat_id

    def chat_get(self, tenant_id: str, chat_id: str) -> Optional[Dict[str, Any]]:
        c = self._chats.get(_chat_key(tenant_id, chat_id))
        if not c:
            return None
        out = {"chat_id": c.chat_id, "title": c.title, "updated_at": c.updated_at}
        if getattr(c, "fingerprint_id", None) is not None:
            out["fingerprint_id"] = c.fingerprint_id
        if getattr(c, "skin_id", None) is not None:
            out["skin_id"] = c.skin_id
        if getattr(c, "swarm_run_id", None) is not None:
            out["swarm_run_id"] = c.swarm_run_id
        if getattr(c, "swarm_role", None) is not None:
            out["swarm_role"] = c.swarm_role
        return out

    def chat_update(self, tenant_id: str, chat_id: str, title: str) -> bool:
        key = _chat_key(tenant_id, chat_id)
        if key not in self._chats:
            return False
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        c = self._chats[key]
        self._chats[key] = ChatRow(
            chat_id=chat_id,
            title=title,
            updated_at=now,
            unread_count=c.unread_count,
            tenant_id=tenant_id,
            fingerprint_id=getattr(c, "fingerprint_id", None),
            skin_id=getattr(c, "skin_id", None),
        )
        return True

    def chat_get_traits(self, tenant_id: str, chat_id: str) -> Dict[str, float]:
        """Effective trait vector for chat (steering). Empty dict if none set."""
        return dict(self._chat_traits.get(_chat_key(tenant_id, chat_id), {}))

    def chat_set_traits(self, tenant_id: str, chat_id: str, traits: Dict[str, float]) -> None:
        """Set effective trait vector for chat (steering)."""
        self._chat_traits[_chat_key(tenant_id, chat_id)] = dict(traits)

    def chat_get_persona_state(self, tenant_id: str, chat_id: str) -> Dict[str, Any]:
        """Session-scoped persona naturalness state for a chat."""
        return dict(self._chat_persona_state.get(_chat_key(tenant_id, chat_id), {}))

    def chat_set_persona_state(self, tenant_id: str, chat_id: str, state: Dict[str, Any]) -> None:
        """Persist session-scoped persona naturalness state for a chat."""
        self._chat_persona_state[_chat_key(tenant_id, chat_id)] = dict(state or {})

    def chat_get_persona_autonomy_state(self, tenant_id: str, chat_id: str) -> Dict[str, Any]:
        """Session-scoped persona autonomy state for a chat."""
        return dict(self._chat_persona_autonomy_state.get(_chat_key(tenant_id, chat_id), {}))

    def chat_set_persona_autonomy_state(self, tenant_id: str, chat_id: str, state: Dict[str, Any]) -> None:
        """Persist session-scoped persona autonomy state for a chat."""
        self._chat_persona_autonomy_state[_chat_key(tenant_id, chat_id)] = dict(state or {})

    def chat_set_deleted(self, tenant_id: str, chat_id: str, deleted: bool, reason: Optional[str] = None) -> bool:
        key = _chat_key(tenant_id, chat_id)
        if key not in self._chats:
            return False
        return True

    def chat_delete(self, tenant_id: str, chat_id: str) -> bool:
        key = _chat_key(tenant_id, chat_id)
        if key not in self._chats:
            return False
        turn_ids = [
            turn_id
            for turn_id, row in self._persona_naturalness_turns.items()
            if row.get("tenant_id") == tenant_id and row.get("chat_id") == chat_id
        ]
        for turn_id in turn_ids:
            self._persona_naturalness_turns.pop(turn_id, None)
        self._persona_naturalness_issues = [
            issue for issue in self._persona_naturalness_issues
            if not (issue.get("tenant_id") == tenant_id and issue.get("turn_id") in turn_ids)
        ]
        autonomy_turn_ids = [
            turn_id
            for turn_id, row in self._persona_autonomy_turns.items()
            if row.get("tenant_id") == tenant_id and row.get("chat_id") == chat_id
        ]
        for turn_id in autonomy_turn_ids:
            self._persona_autonomy_turns.pop(turn_id, None)
        del self._chats[key]
        self._messages.pop(key, None)
        self._agents.pop(key, None)
        self._chat_traits.pop(key, None)
        self._chat_persona_state.pop(key, None)
        self._chat_persona_autonomy_state.pop(key, None)
        return True

    def message_list(self, tenant_id: str, chat_id: str) -> List[Dict[str, Any]]:
        rows = self._messages.get(_chat_key(tenant_id, chat_id), [])
        return [_message_to_dict(m) for m in rows]

    def message_add(
        self,
        tenant_id: str,
        chat_id: str,
        role: str,
        content: str,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_payload: Optional[Dict] = None,
        tool_result: Optional[Dict] = None,
        approvals_required: Optional[bool] = None,
    ) -> MessageRow:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        message_id = str(uuid.uuid4())
        key = _chat_key(tenant_id, chat_id)
        row = MessageRow(
            message_id=message_id,
            chat_id=chat_id,
            role=role,
            created_at=now,
            content=content,
            agent_id=agent_id,
            tool_name=tool_name,
            tool_payload=tool_payload,
            tool_result=tool_result,
            approvals_required=approvals_required,
        )
        self._messages.setdefault(key, []).append(row)
        if key in self._chats:
            c = self._chats[key]
            self._chats[key] = ChatRow(
                chat_id=c.chat_id, title=c.title, updated_at=now,
                unread_count=c.unread_count, tenant_id=tenant_id,
                fingerprint_id=getattr(c, "fingerprint_id", None),
                skin_id=getattr(c, "skin_id", None),
                swarm_run_id=getattr(c, "swarm_run_id", None),
                swarm_role=getattr(c, "swarm_role", None),
            )
        return row

    def agent_list(self, tenant_id: str, chat_id: str) -> List[Dict[str, Any]]:
        rows = self._agents.get(_chat_key(tenant_id, chat_id), [])
        return [
            {
                "agent_id": a.agent_id,
                "label": a.label,
                "status": a.status,
                "parent_agent_id": a.parent_agent_id,
                "lifecycle_state": getattr(a, "lifecycle_state", LIFECYCLE_ACTIVE),
                "state_reason": getattr(a, "state_reason", None),
                "state_updated_at": getattr(a, "state_updated_at", None),
                "state_updated_by": getattr(a, "state_updated_by", None),
                "children": [x.agent_id for x in rows if x.parent_agent_id == a.agent_id],
            }
            for a in rows
        ]

    def agent_get_lifecycle(
        self, tenant_id: str, chat_id: str, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return lifecycle state for an agent, or None if agent not found."""
        rows = self._agents.get(_chat_key(tenant_id, chat_id), [])
        for a in rows:
            if a.agent_id == agent_id:
                return {
                    "lifecycle_state": getattr(a, "lifecycle_state", LIFECYCLE_ACTIVE),
                    "state_reason": getattr(a, "state_reason", None),
                    "state_updated_at": getattr(a, "state_updated_at", None),
                    "state_updated_by": getattr(a, "state_updated_by", None),
                }
        return None

    def agent_set_lifecycle(
        self,
        tenant_id: str,
        chat_id: str,
        agent_id: str,
        lifecycle_state: str,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        """Set lifecycle state for an agent. Returns True if agent was found and updated."""
        key = _chat_key(tenant_id, chat_id)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        agents = self._agents.get(key, [])
        for i, a in enumerate(agents):
            if a.agent_id == agent_id:
                agents[i] = AgentRow(
                    agent_id=a.agent_id,
                    label=a.label,
                    status=a.status,
                    parent_agent_id=a.parent_agent_id,
                    lifecycle_state=lifecycle_state,
                    state_reason=reason,
                    state_updated_at=now,
                    state_updated_by=updated_by or None,
                )
                return True
        return False

    def agent_upsert(
        self,
        tenant_id: str,
        chat_id: str,
        agent_id: str,
        label: str,
        status: str,
        parent_agent_id: Optional[str] = None,
        state_reason: Optional[str] = None,
    ) -> None:
        key = _chat_key(tenant_id, chat_id)
        agents = self._agents.setdefault(key, [])
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if state_reason else None
        for i, a in enumerate(agents):
            if a.agent_id == agent_id:
                agents[i] = AgentRow(
                    agent_id=agent_id,
                    label=label,
                    status=status,
                    parent_agent_id=parent_agent_id,
                    lifecycle_state=getattr(a, "lifecycle_state", LIFECYCLE_ACTIVE),
                    state_reason=state_reason if state_reason is not None else getattr(a, "state_reason", None),
                    state_updated_at=now_iso or getattr(a, "state_updated_at", None),
                    state_updated_by=getattr(a, "state_updated_by", None),
                )
                return
        agents.append(
            AgentRow(
                agent_id=agent_id,
                label=label,
                status=status,
                parent_agent_id=parent_agent_id,
                lifecycle_state=LIFECYCLE_ACTIVE,
                state_reason=state_reason,
                state_updated_at=now_iso,
                state_updated_by=None,
            )
        )

    def approval_list(
        self,
        tenant_id: str,
        status_filter: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        """When limit is set, returns dict with keys 'approvals' (list) and 'total' (int). Otherwise returns list."""
        status_filter = (status_filter or "pending").strip().lower()

        def match(a: Any) -> bool:
            if getattr(a, "tenant_id", "default") != tenant_id:
                return False
            if status_filter == "pending":
                return a.status == "pending"
            if status_filter == "all":
                return True
            return a.status == status_filter

        def to_dict(a: Any) -> Dict[str, Any]:
            return {
                "id": a.id,
                "createdAt": a.created_at,
                "resolvedAt": a.resolved_at,
                "status": a.status,
                "kind": a.kind,
                "title": a.title,
                "summary": a.summary,
                "risk": a.risk,
                "requestedBy": a.requested_by,
                "payload": a.payload,
                "resolutionNote": a.resolution_note,
                "assignedPrincipalId": getattr(a, "assigned_principal_id", None),
                "chat_id": self._lock_approvals.get(a.id),
            }

        filtered = [to_dict(a) for a in self._approvals.values() if match(a)]
        filtered.sort(key=lambda x: (x.get("createdAt") or ""), reverse=True)
        if limit is not None:
            total = len(filtered)
            page = filtered[(offset or 0) : (offset or 0) + limit]
            return {"approvals": page, "total": total}
        return filtered

    def approval_list_for_chat(self, tenant_id: str, chat_id: str) -> List[Dict[str, Any]]:
        """All approvals (any status) linked to this chat. For bundle export."""
        out = []
        for aid, a in self._approvals.items():
            if getattr(a, "tenant_id", "default") != tenant_id:
                continue
            if self._lock_approvals.get(aid) != chat_id:
                continue
            out.append({
                "id": a.id,
                "created_at": a.created_at,
                "resolved_at": a.resolved_at,
                "status": a.status,
                "kind": a.kind,
                "title": a.title,
                "summary": a.summary,
                "risk": a.risk,
                "requested_by": a.requested_by,
                "payload": a.payload,
                "resolution_note": getattr(a, "resolution_note", None),
                "chat_id": chat_id,
            })
        out.sort(key=lambda x: x["created_at"] or "")
        return out

    def approval_add(
        self,
        tenant_id: str,
        kind: str,
        title: str,
        summary: str,
        risk: str,
        requested_by: str,
        payload: Dict[str, Any],
        chat_id: Optional[str] = None,
        assigned_principal_id: Optional[str] = None,
    ) -> str:
        aid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._approvals[aid] = ApprovalRow(
            id=aid, created_at=now, resolved_at=None, status="pending",
            kind=kind, title=title, summary=summary, risk=risk,
            requested_by=requested_by, payload=payload, resolution_note=None,
            assigned_principal_id=assigned_principal_id, tenant_id=tenant_id,
        )
        if chat_id:
            self._lock_approvals[aid] = chat_id
        return aid

    def approval_get(self, tenant_id: str, approval_id: str) -> Optional[Dict[str, Any]]:
        a = self._approvals.get(approval_id)
        if not a or getattr(a, "tenant_id", "default") != tenant_id:
            return None
        chat_id = self._lock_approvals.get(approval_id)
        return {
            "id": a.id,
            "created_at": a.created_at,
            "resolved_at": a.resolved_at,
            "status": a.status,
            "kind": a.kind,
            "title": a.title,
            "summary": getattr(a, "summary", "") or "",
            "risk": getattr(a, "risk", "") or "",
            "payload": a.payload,
            "chat_id": chat_id,
            "assigned_principal_id": getattr(a, "assigned_principal_id", None),
            "resolution_note": getattr(a, "resolution_note", None),
        }

    def approval_resolve(self, tenant_id: str, approval_id: str, decision: str, note: Optional[str] = None) -> bool:
        a = self._approvals.get(approval_id)
        if not a or getattr(a, "tenant_id", "default") != tenant_id:
            return False
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._approvals[approval_id] = ApprovalRow(
            id=a.id, created_at=a.created_at, resolved_at=now, status=decision,
            kind=a.kind, title=a.title, summary=a.summary, risk=a.risk,
            requested_by=a.requested_by, payload=a.payload, resolution_note=note,
            assigned_principal_id=getattr(a, "assigned_principal_id", None), tenant_id=tenant_id,
        )
        return True

    def persona_naturalness_add_turn(self, tenant_id: str, payload: Dict[str, Any]) -> None:
        row = dict(payload or {})
        turn_id = str(row.get("turn_id") or row.get("message_id") or uuid.uuid4())
        created_at = str(row.get("created_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        issues = list(row.pop("issues", []) or [])
        row["turn_id"] = turn_id
        row["tenant_id"] = tenant_id
        row["created_at"] = created_at
        self._persona_naturalness_turns[turn_id] = row
        self._persona_naturalness_issues = [
            issue for issue in self._persona_naturalness_issues
            if not (issue.get("tenant_id") == tenant_id and issue.get("turn_id") == turn_id)
        ]
        for issue in issues:
            if isinstance(issue, str):
                issue_code = issue
                issue_payload: Dict[str, Any] = {}
            else:
                issue_code = str(issue.get("issue_code") or issue.get("code") or "")
                issue_payload = dict(issue.get("payload") or {})
            if not issue_code:
                continue
            self._persona_naturalness_issues.append(
                {
                    "turn_id": turn_id,
                    "tenant_id": tenant_id,
                    "issue_code": issue_code,
                    "payload": issue_payload,
                    "created_at": created_at,
                }
            )

    def persona_naturalness_list(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        cutoff = None
        if hours is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - (float(hours) * 3600.0)
        rows: List[Dict[str, Any]] = []
        for row in self._persona_naturalness_turns.values():
            if row.get("tenant_id") != tenant_id:
                continue
            if fingerprint_id and row.get("fingerprint_id") != fingerprint_id:
                continue
            if skin_id and row.get("skin_id") != skin_id:
                continue
            if chat_id and row.get("chat_id") != chat_id:
                continue
            if swarm_run_id and row.get("swarm_run_id") != swarm_run_id:
                continue
            if cutoff is not None:
                try:
                    created_at = datetime.fromisoformat(str(row.get("created_at") or "").replace("Z", "+00:00")).timestamp()
                except ValueError:
                    created_at = None
                if created_at is None or created_at < cutoff:
                    continue
            rows.append(dict(row))
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        limited = rows[: max(0, int(limit))]
        issues_by_turn: Dict[str, List[Dict[str, Any]]] = {}
        for issue in self._persona_naturalness_issues:
            if issue.get("tenant_id") != tenant_id:
                continue
            issues_by_turn.setdefault(str(issue.get("turn_id") or ""), []).append(
                {
                    "issue_code": issue.get("issue_code"),
                    "payload": dict(issue.get("payload") or {}),
                    "created_at": issue.get("created_at"),
                }
            )
        for row in limited:
            row["issues"] = issues_by_turn.get(str(row.get("turn_id") or ""), [])
        return limited

    def persona_naturalness_summary(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_naturalness_list(
            tenant_id,
            fingerprint_id=fingerprint_id,
            skin_id=skin_id,
            chat_id=chat_id,
            swarm_run_id=swarm_run_id,
            hours=hours,
            limit=10000,
        )
        if not rows:
            return {
                "total_turns": 0,
                "unique_personas": 0,
                "average_sample_overlap": 0.0,
                "average_recent_overlap": 0.0,
                "regeneration_rate": 0.0,
                "regeneration_rescue_rate": 0.0,
                "stress_distribution": {},
                "register_distribution": {},
                "entry_point_distribution": {},
                "tic_frequency": 0.0,
                "top_issue_buckets": {},
            }
        total_turns = len(rows)
        regen_attempted = sum(1 for row in rows if row.get("regeneration_attempted"))
        regen_succeeded = sum(1 for row in rows if row.get("regeneration_succeeded"))
        stress_distribution: Dict[str, int] = {}
        register_distribution: Dict[str, int] = {}
        entry_point_distribution: Dict[str, int] = {}
        issue_buckets: Dict[str, int] = {}
        unique_personas = {
            (str(row.get("fingerprint_id") or ""), str(row.get("skin_id") or ""))
            for row in rows
            if row.get("fingerprint_id")
        }
        for row in rows:
            stress_key = str(row.get("stress_level") or "unknown")
            register_key = str(row.get("chosen_register") or "unknown")
            entry_point_key = str(row.get("chosen_entry_point") or "unknown")
            stress_distribution[stress_key] = stress_distribution.get(stress_key, 0) + 1
            register_distribution[register_key] = register_distribution.get(register_key, 0) + 1
            entry_point_distribution[entry_point_key] = entry_point_distribution.get(entry_point_key, 0) + 1
            for issue in row.get("issues", []) or []:
                code = str(issue.get("issue_code") or "unknown")
                issue_buckets[code] = issue_buckets.get(code, 0) + 1
        return {
            "total_turns": total_turns,
            "unique_personas": len(unique_personas),
            "average_sample_overlap": sum(float(row.get("sample_overlap_score") or 0.0) for row in rows) / total_turns,
            "average_recent_overlap": sum(float(row.get("recent_overlap_score") or 0.0) for row in rows) / total_turns,
            "regeneration_rate": regen_attempted / total_turns,
            "regeneration_rescue_rate": (regen_succeeded / regen_attempted) if regen_attempted else 0.0,
            "stress_distribution": stress_distribution,
            "register_distribution": register_distribution,
            "entry_point_distribution": entry_point_distribution,
            "tic_frequency": sum(int(row.get("tic_count") or 0) for row in rows) / total_turns,
            "top_issue_buckets": issue_buckets,
        }

    def persona_naturalness_swarm_summary(
        self,
        tenant_id: str,
        swarm_run_id: str,
        *,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_naturalness_list(tenant_id, swarm_run_id=swarm_run_id, hours=hours, limit=10000)
        member_breakdown: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            member_key = str(row.get("chat_id") or row.get("turn_id"))
            bucket = member_breakdown.setdefault(
                member_key,
                {
                    "chat_id": row.get("chat_id"),
                    "swarm_role": row.get("swarm_role"),
                    "fingerprint_id": row.get("fingerprint_id"),
                    "skin_id": row.get("skin_id"),
                    "turn_count": 0,
                    "average_sample_overlap": 0.0,
                    "average_recent_overlap": 0.0,
                    "regeneration_attempts": 0,
                    "regeneration_successes": 0,
                    "entry_points": {},
                },
            )
            bucket["turn_count"] += 1
            bucket["average_sample_overlap"] += float(row.get("sample_overlap_score") or 0.0)
            bucket["average_recent_overlap"] += float(row.get("recent_overlap_score") or 0.0)
            bucket["regeneration_attempts"] += 1 if row.get("regeneration_attempted") else 0
            bucket["regeneration_successes"] += 1 if row.get("regeneration_succeeded") else 0
            entry_point_key = str(row.get("chosen_entry_point") or "unknown")
            bucket["entry_points"][entry_point_key] = bucket["entry_points"].get(entry_point_key, 0) + 1
        members: List[Dict[str, Any]] = []
        orchestrator = None
        for bucket in member_breakdown.values():
            turn_count = int(bucket.get("turn_count") or 0)
            if turn_count:
                bucket["average_sample_overlap"] /= turn_count
                bucket["average_recent_overlap"] /= turn_count
            if bucket.get("swarm_role") == "orchestrator":
                orchestrator = dict(bucket)
            else:
                members.append(dict(bucket))
        return {
            "swarm_run_id": swarm_run_id,
            "summary": self.persona_naturalness_summary(tenant_id, swarm_run_id=swarm_run_id, hours=hours),
            "orchestrator": orchestrator,
            "members": members,
        }

    def persona_autonomy_add_turn(self, tenant_id: str, payload: Dict[str, Any]) -> None:
        row = dict(payload or {})
        turn_id = str(row.get("turn_id") or row.get("message_id") or uuid.uuid4())
        row["turn_id"] = turn_id
        row["tenant_id"] = tenant_id
        row["created_at"] = str(row.get("created_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        row["details"] = dict(row.get("details") or {})
        self._persona_autonomy_turns[turn_id] = row

    def persona_autonomy_list(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        cutoff = None
        if hours is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - (float(hours) * 3600.0)
        rows: List[Dict[str, Any]] = []
        for row in self._persona_autonomy_turns.values():
            if row.get("tenant_id") != tenant_id:
                continue
            if fingerprint_id and row.get("fingerprint_id") != fingerprint_id:
                continue
            if skin_id and row.get("skin_id") != skin_id:
                continue
            if chat_id and row.get("chat_id") != chat_id:
                continue
            if swarm_run_id and row.get("swarm_run_id") != swarm_run_id:
                continue
            if cutoff is not None:
                try:
                    created_at = datetime.fromisoformat(str(row.get("created_at") or "").replace("Z", "+00:00")).timestamp()
                except ValueError:
                    created_at = None
                if created_at is None or created_at < cutoff:
                    continue
            rows.append(dict(row))
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return rows[: max(0, int(limit))]

    def persona_autonomy_summary(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_autonomy_list(
            tenant_id,
            fingerprint_id=fingerprint_id,
            skin_id=skin_id,
            chat_id=chat_id,
            swarm_run_id=swarm_run_id,
            hours=hours,
            limit=10000,
        )
        if not rows:
            return {
                "total_turns": 0,
                "arc_distribution": {},
                "engagement_distribution": {},
                "uncertainty_distribution": {},
                "relationship_distribution": {},
                "callback_rate": 0.0,
                "proactive_notice_rate": 0.0,
                "position_evolution_rate": 0.0,
            }
        total_turns = len(rows)
        arc_distribution: Dict[str, int] = {}
        engagement_distribution: Dict[str, int] = {}
        uncertainty_distribution: Dict[str, int] = {}
        relationship_distribution: Dict[str, int] = {}
        callback_count = 0
        proactive_count = 0
        evolution_count = 0
        for row in rows:
            arc_distribution[str(row.get("arc_state") or "unknown")] = arc_distribution.get(str(row.get("arc_state") or "unknown"), 0) + 1
            engagement_distribution[str(row.get("engagement_mode") or "direct")] = engagement_distribution.get(str(row.get("engagement_mode") or "direct"), 0) + 1
            uncertainty_distribution[str(row.get("uncertainty_level") or "confident")] = uncertainty_distribution.get(str(row.get("uncertainty_level") or "confident"), 0) + 1
            relationship_distribution[str(row.get("relationship_type") or "none")] = relationship_distribution.get(str(row.get("relationship_type") or "none"), 0) + 1
            callback_count += 1 if row.get("callback_surface") else 0
            proactive_count += 1 if row.get("proactive_notice") else 0
            evolution_count += 1 if row.get("position_evolution") else 0
        return {
            "total_turns": total_turns,
            "arc_distribution": arc_distribution,
            "engagement_distribution": engagement_distribution,
            "uncertainty_distribution": uncertainty_distribution,
            "relationship_distribution": relationship_distribution,
            "callback_rate": callback_count / total_turns,
            "proactive_notice_rate": proactive_count / total_turns,
            "position_evolution_rate": evolution_count / total_turns,
        }

    def persona_autonomy_swarm_summary(
        self,
        tenant_id: str,
        swarm_run_id: str,
        *,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_autonomy_list(tenant_id, swarm_run_id=swarm_run_id, hours=hours, limit=10000)
        member_breakdown: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            member_key = str(row.get("chat_id") or row.get("turn_id"))
            bucket = member_breakdown.setdefault(
                member_key,
                {
                    "chat_id": row.get("chat_id"),
                    "swarm_role": row.get("swarm_role"),
                    "fingerprint_id": row.get("fingerprint_id"),
                    "relationship_types": {},
                    "engagement_modes": {},
                    "turn_count": 0,
                },
            )
            bucket["turn_count"] += 1
            relationship_key = str(row.get("relationship_type") or "none")
            engagement_key = str(row.get("engagement_mode") or "direct")
            bucket["relationship_types"][relationship_key] = bucket["relationship_types"].get(relationship_key, 0) + 1
            bucket["engagement_modes"][engagement_key] = bucket["engagement_modes"].get(engagement_key, 0) + 1
        orchestrator = None
        members: List[Dict[str, Any]] = []
        for bucket in member_breakdown.values():
            if bucket.get("swarm_role") == "orchestrator":
                orchestrator = dict(bucket)
            else:
                members.append(dict(bucket))
        return {
            "swarm_run_id": swarm_run_id,
            "summary": self.persona_autonomy_summary(tenant_id, swarm_run_id=swarm_run_id, hours=hours),
            "orchestrator": orchestrator,
            "members": members,
        }

    def event_append(self, tenant_id: str, chat_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Optional audit/SSE replay; no-op for in-memory store."""
        pass

    def chat_tenant_id(self, chat_id: str) -> Optional[str]:
        """Return tenant_id that owns this chat_id, or None if not found. Used for cross-tenant detection."""
        for (tid, cid), _ in self._chats.items():
            if cid == chat_id:
                return tid
        return None

    def audit_append(self, tenant_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Record audit event (e.g. cross_tenant_access)."""
        if not hasattr(self, "_audit_events"):
            self._audit_events = []
        self._audit_events.append({
            "event_id": len(self._audit_events) + 1,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": dict(payload or {}),
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        })

    def audit_list(
        self,
        tenant_id: Optional[str] = None,
        *,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        rows = list(getattr(self, "_audit_events", []))
        if tenant_id:
            rows = [r for r in rows if r.get("tenant_id") == tenant_id]
        if event_type:
            rows = [r for r in rows if r.get("event_type") == event_type]
        rows = sorted(rows, key=lambda r: r.get("event_id", 0), reverse=True)
        total = len(rows)
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        return {
            "items": rows[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ---- Pack3 Phase 6: Prompt and model registry ----
    def prompt_create(self, tenant_id: str, name: str, version: str, body: str, owner: str = "system") -> str:
        pid = str(uuid.uuid4())
        self._prompts[pid] = {"id": pid, "tenant_id": tenant_id, "name": name, "version": version, "body": body, "owner": owner, "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        return pid

    def prompt_get(self, tenant_id: str, prompt_id: str) -> Optional[Dict[str, Any]]:
        p = self._prompts.get(prompt_id)
        if not p or (p["tenant_id"] != tenant_id and p["tenant_id"] != "default"):
            return None
        return dict(p)

    def prompt_list(self, tenant_id: str) -> List[Dict[str, Any]]:
        return [dict(p) for p in self._prompts.values() if p["tenant_id"] == tenant_id or p.get("id") == "default"]

    def model_config_create(self, tenant_id: str, version: str, model_id: str, params_json: Dict[str, Any], created_at: Optional[str] = None) -> str:
        cid = str(uuid.uuid4())
        now = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._model_configs[cid] = {"id": cid, "tenant_id": tenant_id, "version": version, "model_id": model_id, "params": params_json or {}, "created_at": now}
        return cid

    def model_config_get(self, tenant_id: str, config_id: str) -> Optional[Dict[str, Any]]:
        c = self._model_configs.get(config_id)
        if not c or (c["tenant_id"] != tenant_id and c["tenant_id"] != "default"):
            return None
        return dict(c)

    def model_config_list(self, tenant_id: str) -> List[Dict[str, Any]]:
        return [dict(c) for c in self._model_configs.values() if c["tenant_id"] == tenant_id or c["tenant_id"] == "default"]

    def turn_provenance_add(self, tenant_id: str, message_id: str, prompt_id: str, model_config_id: str, sampling_params: Dict[str, Any]) -> None:
        self._turn_provenance[message_id] = {"message_id": message_id, "tenant_id": tenant_id, "prompt_id": prompt_id, "model_config_id": model_config_id, "sampling_params": sampling_params or {}, "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}

    def turn_provenance_get(self, tenant_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        p = self._turn_provenance.get(message_id)
        if not p or p.get("tenant_id") != tenant_id:
            return None
        return dict(p)

    # ---- Pack4: Quotas and usage (in-memory for tests) ----
    def quota_get(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        return getattr(self, "_tenant_quotas", {}).get(tenant_id)

    def quota_set(self, tenant_id: str, limits: Dict[str, Any]) -> None:
        if not hasattr(self, "_tenant_quotas"):
            self._tenant_quotas = {}
        self._tenant_quotas[tenant_id] = dict(limits)

    def usage_get(self, tenant_id: str) -> Dict[str, Any]:
        return getattr(self, "_tenant_usage", {}).get(tenant_id, {})

    def usage_set(self, tenant_id: str, counters: Dict[str, Any]) -> None:
        if not hasattr(self, "_tenant_usage"):
            self._tenant_usage = {}
        self._tenant_usage[tenant_id] = dict(counters)

    # ---- Pack 13: Tenant domains and branding (in-memory) ----
    def get_tenant_id_by_hostname(self, hostname: str) -> Optional[str]:
        if not hostname or not hostname.strip():
            return None
        host = hostname.strip().lower().split(":")[0]
        return getattr(self, "_tenant_domains", {}).get(host)

    def get_tenant_settings(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        s = getattr(self, "_tenant_settings", {}).get(tenant_id)
        if not s:
            return None
        out = dict(s)
        out.setdefault("theme", {})
        out.setdefault("support_links", [])
        out.setdefault("first_turn_approval_required", False)
        out.setdefault("auto_approve_kinds", [])
        out.setdefault("approval_rules", [])
        return out

    def tenant_settings_upsert(
        self,
        tenant_id: str,
        display_name: Optional[str] = None,
        status: Optional[str] = None,
        logo_artifact_id: Optional[str] = None,
        theme_json: Optional[Dict[str, Any]] = None,
        support_links_json: Optional[List[Any]] = None,
        first_turn_approval_required: Optional[bool] = None,
        auto_approve_kinds: Optional[List[str]] = None,
        approval_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        _n = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if not hasattr(self, "_tenant_settings"):
            self._tenant_settings = {}
        existing = self._tenant_settings.get(tenant_id, {})
        self._tenant_settings[tenant_id] = {
            "tenant_id": tenant_id,
            "display_name": display_name if display_name is not None else existing.get("display_name", ""),
            "status": status if status is not None else existing.get("status", "active"),
            "logo_artifact_id": logo_artifact_id if logo_artifact_id is not None else existing.get("logo_artifact_id"),
            "theme": theme_json if theme_json is not None else existing.get("theme", {}),
            "support_links": support_links_json if support_links_json is not None else existing.get("support_links", []),
            "first_turn_approval_required": first_turn_approval_required if first_turn_approval_required is not None else existing.get("first_turn_approval_required", False),
            "auto_approve_kinds": auto_approve_kinds if auto_approve_kinds is not None else existing.get("auto_approve_kinds", []),
            "approval_rules": approval_rules if approval_rules is not None else existing.get("approval_rules", []),
            "updated_at": _n,
        }

    def tenant_domain_add(self, hostname: str, tenant_id: str, verified: bool = False) -> None:
        if not hasattr(self, "_tenant_domains"):
            self._tenant_domains = {}
        host = hostname.strip().lower().split(":")[0]
        self._tenant_domains[host] = tenant_id

    def tenant_domain_get(self, hostname: str) -> Optional[Dict[str, Any]]:
        host = hostname.strip().lower().split(":")[0]
        tid = getattr(self, "_tenant_domains", {}).get(host)
        if tid is None:
            return None
        return {"hostname": host, "tenant_id": tid, "verified": True, "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}

    def tenant_domains_list(self, tenant_id: str) -> List[Dict[str, Any]]:
        _n = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        doms = getattr(self, "_tenant_domains", {})
        return [{"hostname": h, "tenant_id": tid, "verified": True, "created_at": _n} for h, tid in doms.items() if tid == tenant_id]

    def tenant_domain_remove(self, hostname: str) -> bool:
        host = hostname.strip().lower().split(":")[0]
        if not hasattr(self, "_tenant_domains") or host not in self._tenant_domains:
            return False
        del self._tenant_domains[host]
        return True

    def tenant_settings_list_ids(self) -> List[str]:
        """Pack 13: List tenant_ids that have tenant_settings."""
        return list(getattr(self, "_tenant_settings", {}).keys())

    def tenant_key_create(self, tenant_id: str) -> Tuple[str, str]:
        import secrets
        import hashlib
        raw_key = "hg_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        key_id = str(uuid.uuid4())
        if not hasattr(self, "_tenant_key_hashes"):
            self._tenant_key_hashes = {}
        self._tenant_key_hashes[key_hash] = tenant_id
        return (raw_key, key_id)

    def tenant_key_lookup(self, api_key: str) -> Optional[str]:
        if not api_key or len(api_key) < 10:
            return None
        import hashlib
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        return getattr(self, "_tenant_key_hashes", {}).get(key_hash)

    def tenant_delete(self, tenant_id: str) -> Dict[str, Any]:
        """Pack3 Phase 7: Hard delete all tenant data (in-memory only). Returns counts."""
        counts: Dict[str, Any] = {}
        to_del = [k for k in self._chats if k[0] == tenant_id]
        for k in to_del:
            del self._chats[k]
            del self._messages[k]
            del self._agents[k]
        counts["chats"] = len(to_del)
        aids = [aid for aid, a in self._approvals.items() if getattr(a, "tenant_id", "default") == tenant_id]
        for aid in aids:
            del self._approvals[aid]
            self._lock_approvals.pop(aid, None)
        counts["approvals"] = len(aids)
        self._prompts = {pid: p for pid, p in self._prompts.items() if p.get("tenant_id") != tenant_id}
        self._model_configs = {cid: c for cid, c in self._model_configs.items() if c.get("tenant_id") != tenant_id}
        self._turn_provenance = {mid: p for mid, p in self._turn_provenance.items() if p.get("tenant_id") != tenant_id}
        if hasattr(self, "_tenant_quotas"):
            self._tenant_quotas.pop(tenant_id, None)
        if hasattr(self, "_tenant_usage"):
            self._tenant_usage.pop(tenant_id, None)
        if hasattr(self, "_tenant_settings"):
            self._tenant_settings.pop(tenant_id, None)
        if hasattr(self, "_tenant_domains"):
            self._tenant_domains = {h: tid for h, tid in self._tenant_domains.items() if tid != tenant_id}
        if hasattr(self, "_tenant_key_hashes"):
            self._tenant_key_hashes = {h: tid for h, tid in self._tenant_key_hashes.items() if tid != tenant_id}
        return counts


def _message_to_dict(m: MessageRow) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "message_id": m.message_id,
        "chat_id": m.chat_id,
        "role": m.role,
        "created_at": m.created_at,
        "content": m.content,
    }
    if m.agent_id:
        d["agent_id"] = m.agent_id
    if m.tool_name:
        d["tool_name"] = m.tool_name
    if m.tool_payload is not None:
        d["tool_payload"] = m.tool_payload
    if m.tool_result is not None:
        d["tool_result"] = m.tool_result
    if m.approvals_required is not None:
        d["approvals_required"] = m.approvals_required
    return d


_store: Optional[Union[InMemoryStore, "SQLiteStore", "PostgresStore"]] = None


def get_store() -> Union[InMemoryStore, "SQLiteStore", "PostgresStore"]:
    """Return the configured store."""
    global _store
    if _store is None:
        backend = (os.environ.get("HG_GATEWAY_STORE") or "sqlite").strip().lower()
        if backend == "sqlite":
            from hg_gateway.store_sqlite import SQLiteStore
            _store = SQLiteStore()
        elif backend == "postgres":
            from hg_gateway.store_postgres import PostgresStore

            _store = PostgresStore()
        else:
            _store = InMemoryStore()
    return _store


def reset_store_for_tests() -> None:
    """Test-only: drop the cached store singleton so the next ``get_store()``
    re-reads ``HG_GATEWAY_STORE`` / ``HG_GATEWAY_DB_PATH`` from the environment.

    The singleton captures its backend + DB path at first construction. Gateway
    and operator_console tests set a per-test ``HG_GATEWAY_DB_PATH``, but under
    xdist a prior test on the same worker may have already built ``_store`` against
    a different path — so later tests silently read/write the wrong store
    (nondeterministic "not found" stragglers that pass in isolation). A per-test
    reset restores isolation. Never call this on a production request path.
    """
    global _store
    _store = None
