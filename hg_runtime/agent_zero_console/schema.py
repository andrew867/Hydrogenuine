"""Agent Zero Conversational Console schemas."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

CONSOLE_SCHEMA_VERSION = "agent-zero-console/1"


def _frozen() -> dict[str, Any]:
    return {
        "authority_created": False,
        "permission_granted": False,
        "advisory_only": True,
        "redaction_applied": True,
        "hidden_chain_of_thought_present": False,
    }


def stable_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k not in {"receipt_hash", "item_hash", "conversation_hash"}}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def new_conversation_id() -> str:
    return f"conv-{uuid.uuid4().hex[:12]}"


def new_message_id() -> str:
    return f"msg-{uuid.uuid4().hex[:12]}"


class ConversationRole(str, Enum):
    OPERATOR = "operator"
    AGENT_ZERO = "agent_zero"
    SYSTEM = "system"


class ConversationMode(str, Enum):
    CHAT = "chat"
    STATUS_QUERY = "status_query"
    MESSAGE_TRIAGE = "message_triage"
    DRAFT_ONLY = "draft_only"


class RequestIntent(str, Enum):
    ANSWER_ONLY = "answer_only"
    DRAFT_ONLY = "draft_only"
    CREATE_OPERATOR_QUEUE_ITEM = "create_operator_queue_item"
    CREATE_WEB_ACTION_QUEUE_ITEM = "create_web_action_queue_item"
    CREATE_SOCIAL_DRAFT = "create_social_draft"
    CREATE_MESSAGE_REPLY_DRAFT = "create_message_reply_draft"
    REQUEST_OPERATOR_REVIEW = "request_operator_review"
    STATUS_SYNTHESIS = "status_synthesis"
    FORBIDDEN = "forbidden"
    FUTURE_PHASE_REQUIRED = "future_phase_required"


class RequestSurface(str, Enum):
    EXCITON = "exciton"
    OPERATOR = "operator"
    WEB = "web"
    SOCIAL = "social"
    EMAIL = "email"
    MESSAGE = "message"
    SHELL = "shell"
    UNKNOWN = "unknown"


class TrustBoundaryVerdict(str, Enum):
    CARGO = "cargo"
    UNTRUSTED = "untrusted"
    MALICIOUS_PATTERN = "malicious_pattern"
    UNKNOWN = "unknown"


@dataclass
class ContextGrant:
    grant_id: str
    source_ref: str
    granted_at: str
    scope: str
    preview_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), **_frozen()}


@dataclass
class ConversationMessage:
    message_id: str
    conversation_id: str
    role: ConversationRole
    mode: ConversationMode
    text_preview: str
    text_hash: str
    created_at: str
    intent: RequestIntent | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "role": self.role.value,
            "mode": self.mode.value,
            "text_preview": self.text_preview,
            "text_hash": self.text_hash,
            "created_at": self.created_at,
            "intent": self.intent.value if self.intent else None,
            **_frozen(),
        }
        return d


@dataclass
class Conversation:
    conversation_id: str
    started_at: str
    mode: ConversationMode = ConversationMode.CHAT
    context_grants: list[ContextGrant] = field(default_factory=list)
    stopped_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "schema": CONSOLE_SCHEMA_VERSION,
            "conversation_id": self.conversation_id,
            "started_at": self.started_at,
            "mode": self.mode.value,
            "context_grants": [g.to_dict() for g in self.context_grants],
            "stopped_at": self.stopped_at,
            **_frozen(),
        }
        d["conversation_hash"] = stable_hash(d)
        return d


@dataclass
class RequestPolicyDecision:
    intent: RequestIntent
    surface: RequestSurface
    allowed: bool
    reason: str
    queue_handoff: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "surface": self.surface.value,
            "allowed": self.allowed,
            "reason": self.reason,
            "queue_handoff": self.queue_handoff,
            **_frozen(),
        }


@dataclass
class ProposedAction:
    proposal_id: str
    conversation_id: str
    intent: RequestIntent
    surface: RequestSurface
    summary: str
    preview_hash: str
    status: str = "proposed"
    queue_item_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "conversation_id": self.conversation_id,
            "intent": self.intent.value,
            "surface": self.surface.value,
            "summary": self.summary,
            "preview_hash": self.preview_hash,
            "status": self.status,
            "queue_item_ref": self.queue_item_ref,
            **_frozen(),
        }


@dataclass
class ConsoleRequest:
    request_id: str
    conversation_id: str
    text: str
    text_hash: str
    intent: RequestIntent
    policy: RequestPolicyDecision
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
            "text_hash": self.text_hash,
            "intent": self.intent.value,
            "policy": self.policy.to_dict(),
            "created_at": self.created_at,
            **_frozen(),
        }


@dataclass
class ConversationReceipt:
    receipt_id: str
    event_type: str
    conversation_id: str
    created_at: str
    payload: dict[str, Any]
    receipt_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        body = {
            "receipt_id": self.receipt_id,
            "event_type": self.event_type,
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
            "payload": self.payload,
            **_frozen(),
        }
        body["receipt_hash"] = stable_hash(body)
        return body


def validate_invariants(payload: dict[str, Any]) -> None:
    from hg_runtime.agent_zero_console.errors import AuthorityInvariantError

    if payload.get("authority_created") is True or payload.get("permission_granted") is True:
        raise AuthorityInvariantError("authority flags must remain false")
    if payload.get("hidden_chain_of_thought_present") is True:
        raise AuthorityInvariantError("hidden chain-of-thought must not be present")


__all__ = [
    "CONSOLE_SCHEMA_VERSION",
    "ConsoleRequest",
    "ContextGrant",
    "Conversation",
    "ConversationMessage",
    "ConversationMode",
    "ConversationReceipt",
    "ConversationRole",
    "ProposedAction",
    "RequestIntent",
    "RequestPolicyDecision",
    "RequestSurface",
    "TrustBoundaryVerdict",
    "new_conversation_id",
    "new_message_id",
    "stable_hash",
    "validate_invariants",
]
