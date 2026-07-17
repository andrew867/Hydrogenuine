"""Auto-approval rule schema — scoped policy, not authority."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.auto_approval_rules.hash import rule_hash

AUTO_APPROVAL_SCHEMA = "auto-approval-rules/1"
AGENT0_ID = "agent0"


def _frozen() -> dict[str, Any]:
    return {"advisory_only": True, "permission_granted": False, "authority_created": False}


def new_rule_id() -> str:
    return f"aar-{uuid.uuid4().hex[:12]}"


def new_receipt_id() -> str:
    return f"aarc-{uuid.uuid4().hex[:12]}"


class AutoApprovalRuleStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
    DRY_RUN_ONLY = "dry_run_only"


class AutoApprovalRuleDecision(str, Enum):
    AUTO_APPROVE_ALLOWED = "AUTO_APPROVE_ALLOWED"
    AUTO_APPROVE_DENIED = "AUTO_APPROVE_DENIED"
    AUTO_APPROVE_DRY_RUN_ONLY = "AUTO_APPROVE_DRY_RUN_ONLY"
    AUTO_APPROVE_EXPIRED = "AUTO_APPROVE_EXPIRED"
    AUTO_APPROVE_REVOKED = "AUTO_APPROVE_REVOKED"
    AUTO_APPROVE_RATE_LIMITED = "AUTO_APPROVE_RATE_LIMITED"
    AUTO_APPROVE_SCOPE_MISMATCH = "AUTO_APPROVE_SCOPE_MISMATCH"
    AUTO_APPROVE_RISK_TOO_HIGH = "AUTO_APPROVE_RISK_TOO_HIGH"
    AUTO_APPROVE_STOP_BLOCKED = "AUTO_APPROVE_STOP_BLOCKED"
    AUTO_APPROVE_PANIC_BLOCKED = "AUTO_APPROVE_PANIC_BLOCKED"
    AUTO_APPROVE_FULL_STOP = "AUTO_APPROVE_FULL_STOP"


@dataclass
class AutoApprovalRuleScope:
    action_type: str
    allowed_surfaces: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    allowed_accounts: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "allowed_surfaces": self.allowed_surfaces,
            "allowed_domains": self.allowed_domains,
            "allowed_accounts": self.allowed_accounts,
            "allowed_tools": self.allowed_tools,
            **_frozen(),
        }


@dataclass
class AutoApprovalRule:
    rule_id: str
    title: str
    description: str
    action_type: str
    allowed_surfaces: list[str]
    max_risk_class: str
    created_at: str
    created_by_operator_ref: str
    expires_at: str
    max_count_per_run: int = 1
    max_count_per_hour: int = 10
    max_count_per_day: int = 50
    allowed_domains: list[str] = field(default_factory=list)
    allowed_accounts: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    required_trust_boundary_verdict: str = "GREEN"
    required_opb_verdict: str = "GREEN"
    required_ipb_verdict: str | None = None
    required_capability_ref: str | None = None
    required_rate_limit_ref: str | None = None
    dry_run_only: bool = False
    require_receipt: bool = True
    require_operator_notification: bool = True
    status: AutoApprovalRuleStatus = AutoApprovalRuleStatus.ACTIVE
    rule_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "auto-approval-rule",
            "version": AUTO_APPROVAL_SCHEMA,
            "rule_id": self.rule_id,
            "title": self.title[:200],
            "description": self.description[:1000],
            "action_type": self.action_type,
            "allowed_surfaces": self.allowed_surfaces,
            "max_risk_class": self.max_risk_class,
            "allowed_domains": self.allowed_domains,
            "allowed_accounts": self.allowed_accounts,
            "allowed_tools": self.allowed_tools,
            "max_count_per_run": self.max_count_per_run,
            "max_count_per_hour": self.max_count_per_hour,
            "max_count_per_day": self.max_count_per_day,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "created_by_operator_ref": self.created_by_operator_ref,
            "required_trust_boundary_verdict": self.required_trust_boundary_verdict,
            "required_opb_verdict": self.required_opb_verdict,
            "required_ipb_verdict": self.required_ipb_verdict,
            "required_capability_ref": self.required_capability_ref,
            "required_rate_limit_ref": self.required_rate_limit_ref,
            "dry_run_only": self.dry_run_only,
            "require_receipt": self.require_receipt,
            "require_operator_notification": self.require_operator_notification,
            "status": self.status.value,
            **_frozen(),
        }
        payload["rule_hash"] = rule_hash({k: v for k, v in payload.items() if k != "rule_hash"})
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "AutoApprovalRule":
        return cls(
            rule_id=data["rule_id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            action_type=data["action_type"],
            allowed_surfaces=list(data.get("allowed_surfaces", [])),
            max_risk_class=data.get("max_risk_class", "read_only"),
            allowed_domains=list(data.get("allowed_domains", [])),
            allowed_accounts=list(data.get("allowed_accounts", [])),
            allowed_tools=list(data.get("allowed_tools", [])),
            max_count_per_run=int(data.get("max_count_per_run", 1)),
            max_count_per_hour=int(data.get("max_count_per_hour", 10)),
            max_count_per_day=int(data.get("max_count_per_day", 50)),
            expires_at=data["expires_at"],
            created_at=data.get("created_at", ""),
            created_by_operator_ref=data["created_by_operator_ref"],
            required_trust_boundary_verdict=data.get("required_trust_boundary_verdict", "GREEN"),
            required_opb_verdict=data.get("required_opb_verdict", "GREEN"),
            required_ipb_verdict=data.get("required_ipb_verdict"),
            required_capability_ref=data.get("required_capability_ref"),
            required_rate_limit_ref=data.get("required_rate_limit_ref"),
            dry_run_only=bool(data.get("dry_run_only", False)),
            require_receipt=bool(data.get("require_receipt", True)),
            require_operator_notification=bool(data.get("require_operator_notification", True)),
            status=AutoApprovalRuleStatus(data.get("status", "active")),
            rule_hash=data.get("rule_hash", ""),
        )


@dataclass
class AutoApprovalRuleReceipt:
    receipt_id: str
    rule_id: str
    event: str
    decision: AutoApprovalRuleDecision
    reason: str
    created_at: str
    operator_ref: str | None = None
    queue_item_id: str | None = None
    receipt_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "auto-approval-receipt",
            "version": AUTO_APPROVAL_SCHEMA,
            "receipt_id": self.receipt_id,
            "rule_id": self.rule_id,
            "event": self.event,
            "decision": self.decision.value,
            "reason": self.reason[:1000],
            "created_at": self.created_at,
            "operator_ref": self.operator_ref,
            "queue_item_id": self.queue_item_id,
            **_frozen(),
        }
        payload["receipt_hash"] = rule_hash({k: v for k, v in payload.items() if k != "receipt_hash"})
        return payload


@dataclass
class AutoApprovalEvaluation:
    decision: AutoApprovalRuleDecision
    reason: str
    rule_id: str | None = None
    receipt_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "rule_id": self.rule_id,
            "receipt_id": self.receipt_id,
            **_frozen(),
        }


@dataclass
class AutoApprovalRevocation:
    rule_id: str
    operator_ref: str
    reason: str
    revoked_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "operator_ref": self.operator_ref,
            "reason": self.reason[:500],
            "revoked_at": self.revoked_at,
            **_frozen(),
        }


__all__ = [
    "AGENT0_ID",
    "AUTO_APPROVAL_SCHEMA",
    "AutoApprovalEvaluation",
    "AutoApprovalRevocation",
    "AutoApprovalRule",
    "AutoApprovalRuleDecision",
    "AutoApprovalRuleReceipt",
    "AutoApprovalRuleScope",
    "AutoApprovalRuleStatus",
    "new_receipt_id",
    "new_rule_id",
]
