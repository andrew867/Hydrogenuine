"""Operator action queue schema — general-purpose operator mediation layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.exciton_action_model.policy_refs import (
    AgentActionCapabilityRef,
    AgentActionPolicyRef,
    AgentActionProofRef,
    AgentActionRateLimitRef,
    OperatorDecisionRef,
)
from hg_runtime.exciton_action_model.risk import AgentActionRiskClass
from hg_runtime.exciton_action_model.schema import AgentActionRequest, AgentActionSurface
from hg_runtime.exciton_action_model.status import AgentActionStatus
from hg_runtime.operator_action_queue.hash import queue_hash

OPERATOR_QUEUE_SCHEMA_VERSION = "operator-action-queue/1"


def _frozen() -> dict[str, Any]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def new_queue_item_id() -> str:
    return f"oqi-{uuid.uuid4().hex[:12]}"


def new_queue_receipt_id() -> str:
    return f"oqr-{uuid.uuid4().hex[:12]}"


# Re-export status as queue status (same lifecycle).
OperatorQueueStatus = AgentActionStatus


class OperatorQueueDecisionType(str, Enum):
    APPROVE_ITEM = "APPROVE_ITEM"
    DENY_ITEM = "DENY_ITEM"
    EXPIRE_ITEM = "EXPIRE_ITEM"
    CANCEL_ITEM = "CANCEL_ITEM"
    MARK_EXECUTED = "MARK_EXECUTED"
    MARK_FAILED = "MARK_FAILED"
    BLOCK_ITEM = "BLOCK_ITEM"
    ENQUEUE_ITEM = "ENQUEUE_ITEM"


@dataclass
class OperatorQueueDecision:
    decision_id: str
    queue_item_id: str
    decision_type: OperatorQueueDecisionType
    operator_ref: str | None
    reason: str
    created_at: str
    previous_status: str
    new_status: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "queue_item_id": self.queue_item_id,
            "decision_type": self.decision_type.value,
            "operator_ref": self.operator_ref,
            "reason": self.reason[:1000],
            "created_at": self.created_at,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            **_frozen(),
        }


@dataclass
class OperatorQueueReceipt:
    receipt_id: str
    queue_item_id: str
    action_id: str
    action_type: str
    decision_type: OperatorQueueDecisionType
    operator_ref: str | None
    reason: str
    created_at: str
    previous_status: str
    new_status: str
    queue_hash_at_transition: str
    previous_receipt_ref: str | None = None
    receipt_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "operator-queue-receipt",
            "version": OPERATOR_QUEUE_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "queue_item_id": self.queue_item_id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "decision_type": self.decision_type.value,
            "operator_ref": self.operator_ref,
            "reason": self.reason[:1000],
            "created_at": self.created_at,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "queue_hash_at_transition": self.queue_hash_at_transition,
            "previous_receipt_ref": self.previous_receipt_ref,
            **_frozen(),
        }
        from hg_runtime.exciton_action_model.hash import action_hash

        payload["receipt_hash"] = action_hash(
            {k: v for k, v in payload.items() if k != "receipt_hash"}
        )
        return payload


@dataclass
class OperatorQueueItem:
    """One queue entry wrapping an action request."""

    queue_item_id: str
    action_request: AgentActionRequest
    previous_item_ref: str | None = None
    queue_hash: str = ""

    @property
    def action_id(self) -> str:
        return self.action_request.action_id

    @property
    def action_type(self) -> str:
        return self.action_request.action_type.value

    @property
    def source_agent(self) -> str:
        return self.action_request.source_agent

    @property
    def source_task(self) -> str:
        return self.action_request.source_task

    @property
    def created_at(self) -> str:
        return self.action_request.created_at

    @property
    def expires_at(self) -> str | None:
        return self.action_request.expires_at

    @property
    def priority(self) -> int:
        return self.action_request.priority

    @property
    def status(self) -> OperatorQueueStatus:
        return self.action_request.status

    @status.setter
    def status(self, value: OperatorQueueStatus) -> None:
        self.action_request.status = value

    @property
    def title(self) -> str:
        return self.action_request.title

    @property
    def human_summary(self) -> str:
        return self.action_request.human_summary

    @property
    def sanitized_preview(self) -> str:
        return self.action_request.sanitized_preview

    @property
    def requested_surface(self) -> AgentActionSurface:
        return self.action_request.requested_surface

    @property
    def risk_class(self) -> AgentActionRiskClass:
        return self.action_request.risk_class

    def to_payload(self) -> dict[str, Any]:
        ar = self.action_request.to_payload()
        payload: dict[str, Any] = {
            "schema": "operator-queue-item",
            "version": OPERATOR_QUEUE_SCHEMA_VERSION,
            "queue_item_id": self.queue_item_id,
            "action_request": ar,
            "action_id": ar["action_id"],
            "action_type": ar["action_type"],
            "source_agent": ar["source_agent"],
            "source_task": ar["source_task"],
            "created_at": ar["created_at"],
            "expires_at": ar.get("expires_at"),
            "priority": ar["priority"],
            "status": ar["status"],
            "title": ar["title"],
            "human_summary": ar["human_summary"],
            "sanitized_preview": ar["sanitized_preview"],
            "requested_surface": ar["requested_surface"],
            "risk_class": ar["risk_class"],
            "trust_boundary_verdict": ar.get("trust_boundary_verdict"),
            "opb_verdict": ar.get("opb_verdict"),
            "ipb_verdict": ar.get("ipb_verdict"),
            "capability_ref": ar.get("capability_ref"),
            "rate_limit_ref": ar.get("rate_limit_ref"),
            "policy_refs": ar.get("policy_refs", []),
            "proof_refs": ar.get("proof_refs", []),
            "operator_decision_ref": ar.get("operator_decision_ref"),
            "execution_receipt_ref": ar.get("execution_receipt_ref"),
            "previous_item_ref": self.previous_item_ref,
            **_frozen(),
        }
        payload["queue_hash"] = queue_hash(
            {k: v for k, v in payload.items() if k != "queue_hash"}
        )
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "OperatorQueueItem":
        ar_data = data.get("action_request") or data
        action_request = AgentActionRequest.from_payload(ar_data)
        if "status" in data and data["status"] != ar_data.get("status"):
            action_request.status = OperatorQueueStatus(data["status"])
        return cls(
            queue_item_id=data["queue_item_id"],
            action_request=action_request,
            previous_item_ref=data.get("previous_item_ref"),
            queue_hash=data.get("queue_hash", ""),
        )

    def refresh_hash(self) -> str:
        self.queue_hash = self.to_payload()["queue_hash"]
        self.action_request.item_hash = self.action_request.to_payload()["item_hash"]
        return self.queue_hash


@dataclass
class OperatorQueueFilter:
    status: OperatorQueueStatus | None = None
    action_type: str | None = None
    source_agent: str | None = None
    risk_class: str | None = None
    surface: str | None = None

    def matches(self, item: OperatorQueueItem) -> bool:
        if self.status is not None and item.status != self.status:
            return False
        if self.action_type is not None and item.action_type != self.action_type:
            return False
        if self.source_agent is not None and item.source_agent != self.source_agent:
            return False
        if self.risk_class is not None and item.risk_class.value != self.risk_class:
            return False
        if self.surface is not None and item.requested_surface.value != self.surface:
            return False
        return True


@dataclass
class OperatorQueueStats:
    total: int = 0
    queued: int = 0
    approved: int = 0
    denied: int = 0
    expired: int = 0
    cancelled: int = 0
    executed: int = 0
    failed: int = 0
    invalid: int = 0
    blocked: int = 0
    dry_run_only: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "queued": self.queued,
            "approved": self.approved,
            "denied": self.denied,
            "expired": self.expired,
            "cancelled": self.cancelled,
            "executed": self.executed,
            "failed": self.failed,
            "invalid": self.invalid,
            "blocked": self.blocked,
            "dry_run_only": self.dry_run_only,
            **_frozen(),
        }


@dataclass
class OperatorQueueSummary:
    stats: OperatorQueueStats
    queue_path: str
    receipts_path: str
    stop_active: bool = False
    panic_active: bool = False
    emergency_lock: bool = False
    degraded_mode: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "stats": self.stats.to_payload(),
            "queue_path": self.queue_path,
            "receipts_path": self.receipts_path,
            "stop_active": self.stop_active,
            "panic_active": self.panic_active,
            "emergency_lock": self.emergency_lock,
            "degraded_mode": self.degraded_mode,
            **_frozen(),
        }


@dataclass
class OperatorActionQueue:
    """In-memory queue state."""

    store_root: str
    items: list[OperatorQueueItem] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "operator-action-queue",
            "version": OPERATOR_QUEUE_SCHEMA_VERSION,
            "store_root": self.store_root,
            "items": [i.to_payload() for i in self.items],
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "OperatorActionQueue":
        return cls(
            store_root=data.get("store_root", ""),
            items=[OperatorQueueItem.from_payload(i) for i in data.get("items", [])],
        )


__all__ = [
    "OPERATOR_QUEUE_SCHEMA_VERSION",
    "OperatorActionQueue",
    "OperatorQueueDecision",
    "OperatorQueueDecisionType",
    "OperatorQueueFilter",
    "OperatorQueueItem",
    "OperatorQueueReceipt",
    "OperatorQueueStats",
    "OperatorQueueStatus",
    "OperatorQueueSummary",
    "new_queue_item_id",
    "new_queue_receipt_id",
]
