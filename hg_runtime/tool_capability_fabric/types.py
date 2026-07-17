"""Tool Capability Fabric types — capabilities are not authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

FABRIC_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-15T01:00:00.000000Z"

CapabilityRiskClass = Literal["low", "medium", "high", "critical"]
CapabilityStatus = Literal["enabled", "disabled", "contract_ready", "operator_review"]

ToolRequestState = Literal[
    "REQUESTED",
    "POLICY_CHECK_STARTED",
    "APPROVED_SCOPED",
    "DENIED",
    "DEFERRED",
    "OPERATOR_REVIEW_REQUIRED",
    "PERMIT_REQUIRED",
    "EXECUTION_ADMITTED",
    "EXECUTION_REFUSED",
    "EXECUTED",
    "FAILED",
    "CANCELLED",
]

ToolDenialReason = Literal[
    "CAPABILITY_DISABLED",
    "LIVE_DISABLED",
    "ORGAN_SCOPE_DENIED",
    "PERMIT_REQUIRED",
    "OPERATOR_REVIEW_REQUIRED",
    "EXTERNAL_NETWORK_REQUIRED",
    "OAUTH_SECRET_REQUIRED",
    "PROVIDER_NOT_CONFIGURED",
    "SHELL_NOT_ALLOWLISTED",
    "WRITE_NOT_ADMITTED",
    "RATE_LIMIT",
    "POLICY_REFUSAL",
]


class CapabilityClass(str, Enum):
    MEMORY_READ = "MEMORY_READ"
    MEMORY_WRITE_REQUEST = "MEMORY_WRITE_REQUEST"
    STORAGE_READ = "STORAGE_READ"
    STORAGE_WRITE_REQUEST = "STORAGE_WRITE_REQUEST"
    PROOF_READ = "PROOF_READ"
    PROOF_VERIFY = "PROOF_VERIFY"
    ARTIFACT_READ = "ARTIFACT_READ"
    ARTIFACT_WRITE_REQUEST = "ARTIFACT_WRITE_REQUEST"
    WEB_SEARCH = "WEB_SEARCH"
    NEWS_SEARCH = "NEWS_SEARCH"
    KNOWLEDGE_LOOKUP = "KNOWLEDGE_LOOKUP"
    SOCIAL_READ = "SOCIAL_READ"
    SOCIAL_DRAFT = "SOCIAL_DRAFT"
    SOCIAL_PUBLISH_REQUEST = "SOCIAL_PUBLISH_REQUEST"
    EMAIL_DRAFT = "EMAIL_DRAFT"
    EMAIL_SEND_REQUEST = "EMAIL_SEND_REQUEST"
    CALENDAR_READ = "CALENDAR_READ"
    CALENDAR_WRITE_REQUEST = "CALENDAR_WRITE_REQUEST"
    GITHUB_READ = "GITHUB_READ"
    GITHUB_WRITE_REQUEST = "GITHUB_WRITE_REQUEST"
    FILE_READ = "FILE_READ"
    FILE_WRITE_REQUEST = "FILE_WRITE_REQUEST"
    SHELL_SAFE = "SHELL_SAFE"
    SHELL_PRIVILEGED_REQUEST = "SHELL_PRIVILEGED_REQUEST"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    OPERATOR_MESSAGE = "OPERATOR_MESSAGE"
    SENSOR_READ = "SENSOR_READ"
    OEA_ACTION_REQUEST = "OEA_ACTION_REQUEST"
    TER_TOOL_REQUEST = "TER_TOOL_REQUEST"
    CAPABILITY_MANIFEST = "CAPABILITY_MANIFEST"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


def advisory_envelope(**extra: Any) -> dict[str, Any]:
    base = {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "is_permit": False,
        "live_side_effect": False,
        "executed": False,
    }
    base.update(extra)
    if base.get("permission_granted") is True or base.get("authority_created") is True:
        raise ValueError("tool capability fabric must not grant permission or authority")
    return base


def stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class CapabilityDefinition:
    capability_id: str
    name: str
    capability_class: str
    provider: str
    enabled: bool = False
    live_enabled: bool = False
    draft_only: bool = False
    read_only: bool = False
    requires_operator_approval: bool = False
    requires_gpp_permit: bool = False
    requires_ueak_admission: bool = False
    requires_oauth_secret: bool = False
    external_network_required: bool = False
    data_policy: str = "advisory"
    retention_policy: str = "session"
    risk_class: CapabilityRiskClass = "low"
    allowed_roles: list[str] = field(default_factory=list)
    allowed_organs: list[str] = field(default_factory=list)
    default_timeout_seconds: int = 30
    max_rate: int = 60
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="capability-definition",
            capability_id=self.capability_id,
            name=self.name,
            capability_class=self.capability_class,
            provider=self.provider,
            enabled=self.enabled,
            live_enabled=self.live_enabled,
            draft_only=self.draft_only,
            read_only=self.read_only,
            requires_operator_approval=self.requires_operator_approval,
            requires_gpp_permit=self.requires_gpp_permit,
            requires_ueak_admission=self.requires_ueak_admission,
            requires_oauth_secret=self.requires_oauth_secret,
            external_network_required=self.external_network_required,
            data_policy=self.data_policy,
            retention_policy=self.retention_policy,
            risk_class=self.risk_class,
            allowed_roles=self.allowed_roles,
            allowed_organs=self.allowed_organs,
            default_timeout_seconds=self.default_timeout_seconds,
            max_rate=self.max_rate,
        )


@dataclass
class ToolRequest:
    request_id: str
    run_id: str
    agent_id: str
    organ_id: str
    capability_id: str
    requested_action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    intent: str = "advisory"

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="tool-request",
            request_id=self.request_id,
            run_id=self.run_id,
            agent_id=self.agent_id,
            organ_id=self.organ_id,
            capability_id=self.capability_id,
            requested_action=self.requested_action,
            parameters=self.parameters,
            intent=self.intent,
        )


@dataclass
class ToolApprovalReceipt:
    request_id: str
    run_id: str
    organ_id: str
    capability_id: str
    scope: dict[str, Any]
    expires_at: str
    rate_limit: int
    allowed_operation: str
    state: ToolRequestState = "APPROVED_SCOPED"

    def to_payload(self) -> dict[str, Any]:
        payload = advisory_envelope(
            schema="tool-approval-receipt",
            request_id=self.request_id,
            run_id=self.run_id,
            organ_id=self.organ_id,
            capability_id=self.capability_id,
            scope=self.scope,
            expires_at=self.expires_at,
            rate_limit=self.rate_limit,
            allowed_operation=self.allowed_operation,
            policy_result=self.state,
            permit_required=False,
            operator_required=False,
            executed=False,
            timestamp=FIXTURE_CLOCK,
        )
        payload["receipt_hash"] = stable_hash(payload)
        return payload


@dataclass
class ToolDenialReceipt:
    request_id: str
    run_id: str
    organ_id: str
    capability_id: str
    denial_reason: str
    explanation: str
    safe_alternative: str
    missing_requirement: str = ""
    permit_required: bool = False
    operator_required: bool = False
    state: ToolRequestState = "DENIED"

    def to_payload(self) -> dict[str, Any]:
        payload = advisory_envelope(
            schema="tool-denial-receipt",
            request_id=self.request_id,
            run_id=self.run_id,
            organ_id=self.organ_id,
            capability_id=self.capability_id,
            policy_result=self.state,
            denial_reason=self.denial_reason,
            explanation=self.explanation,
            safe_alternative=self.safe_alternative,
            missing_requirement=self.missing_requirement,
            permit_required=self.permit_required,
            operator_required=self.operator_required,
            executed=False,
            timestamp=FIXTURE_CLOCK,
        )
        payload["receipt_hash"] = stable_hash(payload)
        return payload


@dataclass
class ToolExecutionReceipt:
    request_id: str
    run_id: str
    organ_id: str
    capability_id: str
    success: bool
    result_summary: str
    result_ref: str = "hash-only"
    live_side_effect: bool = False
    state: ToolRequestState = "EXECUTED"

    def to_payload(self) -> dict[str, Any]:
        payload = advisory_envelope(
            schema="tool-execution-receipt",
            request_id=self.request_id,
            run_id=self.run_id,
            organ_id=self.organ_id,
            capability_id=self.capability_id,
            policy_result=self.state,
            success=self.success,
            result_summary=self.result_summary,
            result_ref=self.result_ref,
            live_side_effect=self.live_side_effect,
            executed=True,
            timestamp=FIXTURE_CLOCK,
        )
        payload["receipt_hash"] = stable_hash(payload)
        return payload


__all__ = [
    "CapabilityClass",
    "CapabilityDefinition",
    "FABRIC_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "ToolApprovalReceipt",
    "ToolDenialReceipt",
    "ToolExecutionReceipt",
    "ToolRequest",
    "advisory_envelope",
    "stable_hash",
]
