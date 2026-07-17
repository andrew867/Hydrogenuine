"""EXCITON UX Phase 3 action model schema — requests, decisions, receipts.

The action model describes requests. It does not authorize execution.
``authority_created`` and ``permission_granted`` are structurally frozen False.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.hash import action_hash
from hg_runtime.exciton_action_model.policy_refs import (
    ActionExecutionRef,
    AgentActionCapabilityRef,
    AgentActionPolicyRef,
    AgentActionProofRef,
    AgentActionRateLimitRef,
    OperatorDecisionRef,
)
from hg_runtime.exciton_action_model.risk import AgentActionRiskClass
from hg_runtime.exciton_action_model.status import AgentActionStatus

ACTION_MODEL_SCHEMA_VERSION = "exciton-action-model/1"
FIXTURE_UTC = "2026-06-15T04:00:00+00:00"


def _frozen() -> dict[str, Any]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def new_action_id() -> str:
    return f"act-{uuid.uuid4().hex[:12]}"


def new_receipt_id() -> str:
    return f"arec-{uuid.uuid4().hex[:12]}"


class AgentActionSurface(str, Enum):
    EXCITON = "exciton"
    SOCIAL = "social"
    WEB = "web"
    EMAIL = "email"
    CALENDAR = "calendar"
    FILESYSTEM = "filesystem"
    MEMORY = "memory"
    SOURCE = "source"
    ANCHOR = "anchor"
    TOOL = "tool"
    SHELL = "shell"
    ACCOUNT = "account"
    API = "api"
    PUBLICATION = "publication"
    OPERATOR = "operator"
    PROOF = "proof"
    SOAK = "soak"
    CONTROL = "control"
    UNKNOWN = "unknown"


class AgentActionDecisionKind(str, Enum):
    QUEUE_FOR_OPERATOR = "QUEUE_FOR_OPERATOR"
    ALLOW_READ_ONLY = "ALLOW_READ_ONLY"
    ALLOW_DRAFT_ONLY = "ALLOW_DRAFT_ONLY"
    DENY = "DENY"
    FULL_STOP = "FULL_STOP"
    DRY_RUN_ONLY = "DRY_RUN_ONLY"
    REQUIRE_OPERATOR_CONFIRMATION = "REQUIRE_OPERATOR_CONFIRMATION"
    REQUIRE_PERMIT = "REQUIRE_PERMIT"
    RATE_LIMITED = "RATE_LIMITED"
    BLOCKED_BY_PANIC = "BLOCKED_BY_PANIC"
    BLOCKED_BY_STOP = "BLOCKED_BY_STOP"


@dataclass
class AgentActionPreview:
    """Sanitized preview safe for UI display."""

    title: str
    summary: str
    detail_lines: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "title": self.title[:200],
            "summary": self.summary[:1000],
            "detail_lines": [line[:500] for line in self.detail_lines[:20]],
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionPreview":
        return cls(
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            detail_lines=list(data.get("detail_lines", [])),
        )


@dataclass
class AgentActionRequest:
    """Operator-reviewed action request. Never grants authority."""

    action_id: str
    action_type: AgentActionType
    source_agent: str
    source_task: str
    created_at: str
    priority: int
    status: AgentActionStatus
    title: str
    human_summary: str
    sanitized_preview: str
    requested_surface: AgentActionSurface
    risk_class: AgentActionRiskClass
    policy_refs: list[AgentActionPolicyRef] = field(default_factory=list)
    proof_refs: list[AgentActionProofRef] = field(default_factory=list)
    expires_at: str | None = None
    raw_payload_ref: str | None = None
    required_permit_type: str | None = None
    trust_boundary_verdict: str | None = None
    opb_verdict: str | None = None
    ipb_verdict: str | None = None
    capability_ref: AgentActionCapabilityRef | None = None
    rate_limit_ref: AgentActionRateLimitRef | None = None
    operator_decision_ref: OperatorDecisionRef | None = None
    execution_receipt_ref: str | None = None
    item_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "agent-action-request",
            "version": ACTION_MODEL_SCHEMA_VERSION,
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "source_agent": self.source_agent,
            "source_task": self.source_task,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "priority": self.priority,
            "status": self.status.value,
            "title": self.title[:200],
            "human_summary": self.human_summary[:2000],
            "sanitized_preview": self.sanitized_preview[:2000],
            "raw_payload_ref": self.raw_payload_ref,
            "requested_surface": self.requested_surface.value,
            "risk_class": self.risk_class.value,
            "required_permit_type": self.required_permit_type,
            "trust_boundary_verdict": self.trust_boundary_verdict,
            "opb_verdict": self.opb_verdict,
            "ipb_verdict": self.ipb_verdict,
            "capability_ref": self.capability_ref.to_payload() if self.capability_ref else None,
            "rate_limit_ref": self.rate_limit_ref.to_payload() if self.rate_limit_ref else None,
            "policy_refs": [p.to_payload() for p in self.policy_refs],
            "proof_refs": [p.to_payload() for p in self.proof_refs],
            "operator_decision_ref": (
                self.operator_decision_ref.to_payload() if self.operator_decision_ref else None
            ),
            "execution_receipt_ref": self.execution_receipt_ref,
            **_frozen(),
        }
        payload["item_hash"] = action_hash(
            {k: v for k, v in payload.items() if k != "item_hash"}
        )
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionRequest":
        cap = data.get("capability_ref")
        rate = data.get("rate_limit_ref")
        op_dec = data.get("operator_decision_ref")
        return cls(
            action_id=data["action_id"],
            action_type=AgentActionType(data["action_type"]),
            source_agent=data["source_agent"],
            source_task=data.get("source_task", ""),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at"),
            priority=int(data.get("priority", 0)),
            status=AgentActionStatus(data["status"]),
            title=data.get("title", ""),
            human_summary=data["human_summary"],
            sanitized_preview=data.get("sanitized_preview", ""),
            raw_payload_ref=data.get("raw_payload_ref"),
            requested_surface=AgentActionSurface(data.get("requested_surface", "unknown")),
            risk_class=AgentActionRiskClass(data["risk_class"]),
            required_permit_type=data.get("required_permit_type"),
            trust_boundary_verdict=data.get("trust_boundary_verdict"),
            opb_verdict=data.get("opb_verdict"),
            ipb_verdict=data.get("ipb_verdict"),
            capability_ref=AgentActionCapabilityRef.from_payload(cap) if cap else None,
            rate_limit_ref=AgentActionRateLimitRef.from_payload(rate) if rate else None,
            policy_refs=[
                AgentActionPolicyRef.from_payload(p) for p in data.get("policy_refs", [])
            ],
            proof_refs=[AgentActionProofRef.from_payload(p) for p in data.get("proof_refs", [])],
            operator_decision_ref=OperatorDecisionRef.from_payload(op_dec) if op_dec else None,
            execution_receipt_ref=data.get("execution_receipt_ref"),
            item_hash=data.get("item_hash", ""),
        )


@dataclass
class AgentActionDecision:
    """Boundary decision for an action. Display/route only — never grants authority."""

    decision_id: str
    action_id: str
    action_type: AgentActionType
    decision: AgentActionDecisionKind
    reason: str
    created_at: str
    policy_refs: list[AgentActionPolicyRef] = field(default_factory=list)
    proof_refs: list[AgentActionProofRef] = field(default_factory=list)
    operator_ref: str | None = None
    decision_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "agent-action-decision",
            "version": ACTION_MODEL_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "decision": self.decision.value,
            "reason": self.reason[:1000],
            "operator_ref": self.operator_ref,
            "policy_refs": [p.to_payload() for p in self.policy_refs],
            "proof_refs": [p.to_payload() for p in self.proof_refs],
            "created_at": self.created_at,
            **_frozen(),
        }
        payload["decision_hash"] = action_hash(
            {k: v for k, v in payload.items() if k != "decision_hash"}
        )
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionDecision":
        return cls(
            decision_id=data["decision_id"],
            action_id=data["action_id"],
            action_type=AgentActionType(data["action_type"]),
            decision=AgentActionDecisionKind(data["decision"]),
            reason=data.get("reason", ""),
            operator_ref=data.get("operator_ref"),
            policy_refs=[
                AgentActionPolicyRef.from_payload(p) for p in data.get("policy_refs", [])
            ],
            proof_refs=[AgentActionProofRef.from_payload(p) for p in data.get("proof_refs", [])],
            created_at=data.get("created_at", ""),
            decision_hash=data.get("decision_hash", ""),
        )


@dataclass
class AgentActionReceipt:
    """Receipt proving a decision or transition. Never grants authority."""

    receipt_id: str
    action_id: str
    action_type: AgentActionType
    decision: AgentActionDecisionKind
    reason: str
    created_at: str
    policy_refs: list[AgentActionPolicyRef] = field(default_factory=list)
    proof_refs: list[AgentActionProofRef] = field(default_factory=list)
    operator_ref: str | None = None
    previous_receipt_ref: str | None = None
    receipt_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "agent-action-receipt",
            "version": ACTION_MODEL_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "decision": self.decision.value,
            "reason": self.reason[:1000],
            "operator_ref": self.operator_ref,
            "policy_refs": [p.to_payload() for p in self.policy_refs],
            "proof_refs": [p.to_payload() for p in self.proof_refs],
            "created_at": self.created_at,
            "previous_receipt_ref": self.previous_receipt_ref,
            **_frozen(),
        }
        payload["receipt_hash"] = action_hash(
            {k: v for k, v in payload.items() if k != "receipt_hash"}
        )
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AgentActionReceipt":
        return cls(
            receipt_id=data["receipt_id"],
            action_id=data["action_id"],
            action_type=AgentActionType(data["action_type"]),
            decision=AgentActionDecisionKind(data["decision"]),
            reason=data.get("reason", ""),
            operator_ref=data.get("operator_ref"),
            policy_refs=[
                AgentActionPolicyRef.from_payload(p) for p in data.get("policy_refs", [])
            ],
            proof_refs=[AgentActionProofRef.from_payload(p) for p in data.get("proof_refs", [])],
            created_at=data.get("created_at", ""),
            previous_receipt_ref=data.get("previous_receipt_ref"),
            receipt_hash=data.get("receipt_hash", ""),
        )


__all__ = [
    "ACTION_MODEL_SCHEMA_VERSION",
    "FIXTURE_UTC",
    "ActionExecutionRef",
    "AgentActionDecision",
    "AgentActionDecisionKind",
    "AgentActionPreview",
    "AgentActionReceipt",
    "AgentActionRequest",
    "AgentActionSurface",
    "new_action_id",
    "new_receipt_id",
]
