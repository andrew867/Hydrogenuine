"""OEA bounded external actuation types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Mapping, Tuple

RiskClass = Literal["harmless", "low", "medium", "high", "prohibited"]
EffectType = Literal[
    "file_write",
    "local_report",
    "notification",
    "api_call",
    "device_io",
    "social_post",
    "deployment",
    "other",
]
BindingStatus = Literal[
    "created",
    "refused",
    "dry_run_required",
    "confirmation_required",
    "execution_authorized",
    "executing",
    "executed",
    "failed",
    "timed_out",
    "compensated",
    "compensation_failed",
    "closed",
]
ExecutionResultStatus = Literal[
    "executed",
    "refused",
    "failed",
    "timed_out",
    "dry_run_required",
    "confirmation_required",
    "compensation_required",
    "compensated",
    "compensation_failed",
]
CompensationStatus = Literal["none", "pending", "completed", "failed"]
RetryPolicyKind = Literal["none", "idempotent_limited"]


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    name: str
    description: str
    risk_class: RiskClass
    effect_type: EffectType
    enabled_by_default: bool
    requires_human_confirmation: bool
    requires_dry_run: bool
    requires_compensation_plan: bool
    allowed_argument_schema: Mapping[str, Any]
    forbidden_argument_patterns: Tuple[str, ...] = ()
    secret_requirements: Tuple[str, ...] = ()
    timeout_seconds: float = 5.0
    retry_policy: RetryPolicyKind = "none"
    max_retries: int = 0
    compensation_policy: str = "record_only"
    authority_requirements: Tuple[str, ...] = ("ueak_commit_ref",)
    receipt_schema_version: str = "oea_effect_receipt_v1"
    idempotent: bool = False
    max_concurrency: int = 1

    def to_payload(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "risk_class": self.risk_class,
            "effect_type": self.effect_type,
            "enabled_by_default": self.enabled_by_default,
            "requires_human_confirmation": self.requires_human_confirmation,
            "requires_dry_run": self.requires_dry_run,
            "requires_compensation_plan": self.requires_compensation_plan,
            "allowed_argument_schema": dict(self.allowed_argument_schema),
            "forbidden_argument_patterns": list(self.forbidden_argument_patterns),
            "secret_requirements": list(self.secret_requirements),
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": self.retry_policy,
            "max_retries": self.max_retries,
            "compensation_policy": self.compensation_policy,
            "authority_requirements": list(self.authority_requirements),
            "receipt_schema_version": self.receipt_schema_version,
            "idempotent": self.idempotent,
        }


@dataclass(frozen=True)
class OEABinding:
    binding_id: str
    created_at: str
    capability_id: str
    authority_ref: str
    ueak_commit_ref: str
    gpp_permit_ref: str | None
    hal_or_soar_ref: str | None
    requested_by: str
    input_hash: str
    argument_schema_hash: str
    risk_class: RiskClass
    confirmation_ref: str | None = None
    dry_run_ref: str | None = None
    expires_at: str | None = None
    status: BindingStatus = "created"
    arguments: Mapping[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "created_at": self.created_at,
            "capability_id": self.capability_id,
            "authority_ref": self.authority_ref,
            "ueak_commit_ref": self.ueak_commit_ref,
            "gpp_permit_ref": self.gpp_permit_ref,
            "hal_or_soar_ref": self.hal_or_soar_ref,
            "requested_by": self.requested_by,
            "input_hash": self.input_hash,
            "argument_schema_hash": self.argument_schema_hash,
            "risk_class": self.risk_class,
            "confirmation_ref": self.confirmation_ref,
            "dry_run_ref": self.dry_run_ref,
            "expires_at": self.expires_at,
            "status": self.status,
            "arguments": dict(self.arguments),
        }


@dataclass(frozen=True)
class DryRunResult:
    dry_run_id: str
    capability_id: str
    input_hash: str
    predicted_effect: str
    touched_resources: Tuple[str, ...]
    risk_class: RiskClass
    allowed: bool
    refusal_reason: str | None = None
    dry_run_hash: str = ""
    created_at: str = ""

    def to_payload(self) -> Dict[str, Any]:
        payload = {
            "dry_run_id": self.dry_run_id,
            "capability_id": self.capability_id,
            "input_hash": self.input_hash,
            "predicted_effect": self.predicted_effect,
            "touched_resources": list(self.touched_resources),
            "risk_class": self.risk_class,
            "allowed": self.allowed,
            "refusal_reason": self.refusal_reason,
            "dry_run_hash": self.dry_run_hash,
        }
        if self.created_at:
            payload["created_at"] = self.created_at
        return payload


@dataclass(frozen=True)
class EffectReceipt:
    receipt_id: str
    binding_id: str
    capability_id: str
    authority_ref: str
    ueak_commit_ref: str
    input_hash: str
    result_status: ExecutionResultStatus
    output_hash: str
    touched_resources: Tuple[str, ...]
    started_at: str
    completed_at: str
    error_class: str | None = None
    error_message_redacted: str | None = None
    retry_count: int = 0
    compensation_status: CompensationStatus = "none"
    receipt_hash: str = ""
    previous_receipt_hash: str | None = None
    executor_mode: str = "real"
    # Slice 2 dispatch fields — emitted only when set so pre-Slice-2 receipt
    # hashes are unchanged. external_effect_performed stays False for every
    # fake_sink/sandboxed dispatch; only a future operator-gated real tranche
    # may ever set it True.
    permit_id: str = ""
    handoff_id: str = ""
    sink_type: str = ""
    dispatch_mode: str = ""
    external_effect_performed: bool | None = None

    def to_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "receipt_id": self.receipt_id,
            "binding_id": self.binding_id,
            "capability_id": self.capability_id,
            "authority_ref": self.authority_ref,
            "ueak_commit_ref": self.ueak_commit_ref,
            "input_hash": self.input_hash,
            "result_status": self.result_status,
            "output_hash": self.output_hash,
            "touched_resources": list(self.touched_resources),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
            "compensation_status": self.compensation_status,
            "executor_mode": self.executor_mode,
        }
        if self.error_class is not None:
            payload["error_class"] = self.error_class
        if self.error_message_redacted is not None:
            payload["error_message_redacted"] = self.error_message_redacted
        if self.receipt_hash:
            payload["receipt_hash"] = self.receipt_hash
        if self.previous_receipt_hash:
            payload["previous_receipt_hash"] = self.previous_receipt_hash
        if self.permit_id:
            payload["permit_id"] = self.permit_id
        if self.handoff_id:
            payload["handoff_id"] = self.handoff_id
        if self.sink_type:
            payload["sink_type"] = self.sink_type
        if self.dispatch_mode:
            payload["dispatch_mode"] = self.dispatch_mode
        if self.external_effect_performed is not None:
            payload["external_effect_performed"] = self.external_effect_performed
        return payload


__all__ = [
    "BindingStatus",
    "CapabilityDefinition",
    "CompensationStatus",
    "DryRunResult",
    "EffectReceipt",
    "EffectType",
    "ExecutionResultStatus",
    "OEABinding",
    "RetryPolicyKind",
    "RiskClass",
]
