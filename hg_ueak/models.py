"""UEAK execution authority models — admission only; no authority invention."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_gpp.models import GovernedPermit

UEAK_RECEIPT_SCHEMA = "ueak-execution-receipt"
UEAK_RECEIPT_SCHEMA_VERSION = "1.0"
UEAK_DECISION_SCHEMA = "ueak-admission-decision"
UEAK_DECISION_SCHEMA_VERSION = "1.0"

AdmissionStatus = Literal["admitted", "refused"]


@dataclass(frozen=True)
class ExecutionRefusalReason:
    code: str
    detail: str = ""

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class ExecutionCandidate:
    candidate_id: str
    action_type: str
    capability_id: str
    effect_class: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "action_type": self.action_type,
            "capability_id": self.capability_id,
            "effect_class": self.effect_class,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class AuthorityChain:
    """Authority chain refs — SOAR/HAL fixture refs allowed; SOAR not claimed complete."""

    proposal_ref: str
    hal_decision_ref: Optional[str] = None
    soar_run_ref: Optional[str] = None
    gpp_permit_id: Optional[str] = None
    gpp_permit_hash: Optional[str] = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "proposal_ref": self.proposal_ref,
            "hal_decision_ref": self.hal_decision_ref,
            "soar_run_ref": self.soar_run_ref,
            "gpp_permit_id": self.gpp_permit_id,
            "gpp_permit_hash": self.gpp_permit_hash,
        }


@dataclass(frozen=True)
class PermitBinding:
    permit_id: str
    permit_hash: str
    capability_ref: str
    effect_class: str

    def to_payload(self) -> dict[str, str]:
        return {
            "permit_id": self.permit_id,
            "permit_hash": self.permit_hash,
            "capability_ref": self.capability_ref,
            "effect_class": self.effect_class,
        }


@dataclass(frozen=True)
class EmergencyState:
    active: bool = False
    mode: str = "none"
    restrict_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "mode": self.mode,
            "restrict_only": self.restrict_only,
        }


@dataclass(frozen=True)
class ExposureSurface:
    current_level: str = "internal"
    requested_level: str = "internal"
    increase_explicit: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "current_level": self.current_level,
            "requested_level": self.requested_level,
            "increase_explicit": self.increase_explicit,
        }

    def is_increase(self) -> bool:
        levels = {"internal": 0, "bounded": 1, "external": 2}
        return levels.get(self.requested_level, 0) > levels.get(self.current_level, 0)


@dataclass(frozen=True)
class ResourceGovernanceEnvelope:
    pressure_high: bool = False
    quota_available: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "pressure_high": self.pressure_high,
            "quota_available": self.quota_available,
        }


@dataclass(frozen=True)
class RollbackRequirement:
    required: bool
    rollback_ref: str = ""
    compensation_ref: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "rollback_ref": self.rollback_ref,
            "compensation_ref": self.compensation_ref,
        }


@dataclass(frozen=True)
class ExecutionRiskEnvelope:
    risk_class: str = "low"
    exposure: ExposureSurface = field(default_factory=ExposureSurface)
    emergency: EmergencyState = field(default_factory=EmergencyState)
    resource: ResourceGovernanceEnvelope = field(default_factory=ResourceGovernanceEnvelope)

    def to_payload(self) -> dict[str, Any]:
        return {
            "risk_class": self.risk_class,
            "exposure": self.exposure.to_payload(),
            "emergency": self.emergency.to_payload(),
            "resource": self.resource.to_payload(),
        }


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    candidate: ExecutionCandidate
    authority_chain: AuthorityChain
    permit: Optional[GovernedPermit]
    identity_ref: str
    admission_ref: str
    freshness_ref: str
    approval_expires_at: Optional[str]
    redaction_ref: str
    retention_ref: str
    rollback: RollbackRequirement
    risk: ExecutionRiskEnvelope
    panic_lockdown: bool = False
    redaction_payload: Optional[dict[str, Any]] = None
    idempotency_key: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "ueak-execution-request",
            "schema_version": "1.0",
            "request_id": self.request_id,
            "candidate": self.candidate.to_payload(),
            "authority_chain": self.authority_chain.to_payload(),
            "permit_id": self.permit.permit_id if self.permit else None,
            "identity_ref": self.identity_ref,
            "admission_ref": self.admission_ref,
            "freshness_ref": self.freshness_ref,
            "approval_expires_at": self.approval_expires_at,
            "redaction_ref": self.redaction_ref,
            "retention_ref": self.retention_ref,
            "rollback": self.rollback.to_payload(),
            "risk": self.risk.to_payload(),
            "panic_lockdown": self.panic_lockdown,
            "idempotency_key": self.idempotency_key or self.request_id,
        }


@dataclass(frozen=True)
class ExecutionDispatchPlan:
    dispatch_id: str
    request_id: str
    candidate_id: str
    capability_id: str
    effect_class: str
    permit_binding: PermitBinding
    sink: str = "fake_dispatch"

    def to_payload(self) -> dict[str, Any]:
        return {
            "dispatch_id": self.dispatch_id,
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "capability_id": self.capability_id,
            "effect_class": self.effect_class,
            "permit_binding": self.permit_binding.to_payload(),
            "sink": self.sink,
        }


@dataclass(frozen=True)
class ExecutionReceipt:
    receipt_id: str
    request_id: str
    status: AdmissionStatus
    permit_id: str
    issued_at: str
    dispatch_id: Optional[str] = None
    refusal_reasons: tuple[ExecutionRefusalReason, ...] = ()
    receipt_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": UEAK_RECEIPT_SCHEMA,
            "schema_version": UEAK_RECEIPT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "status": self.status,
            "permit_id": self.permit_id,
            "issued_at": self.issued_at,
            "dispatch_id": self.dispatch_id,
            "refusal_reasons": [r.to_payload() for r in self.refusal_reasons],
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


@dataclass(frozen=True)
class ExecutionAdmissionDecision:
    status: AdmissionStatus
    request_id: str
    dispatch_plan: Optional[ExecutionDispatchPlan] = None
    receipt: Optional[ExecutionReceipt] = None
    refusal_reasons: tuple[ExecutionRefusalReason, ...] = ()
    decision_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": UEAK_DECISION_SCHEMA,
            "schema_version": UEAK_DECISION_SCHEMA_VERSION,
            "status": self.status,
            "request_id": self.request_id,
            "refusal_reasons": [r.to_payload() for r in self.refusal_reasons],
        }
        if self.dispatch_plan is not None:
            payload["dispatch_plan"] = self.dispatch_plan.to_payload()
        if self.receipt is not None:
            payload["receipt"] = self.receipt.to_payload()
        if include_hash:
            payload["decision_hash"] = self.decision_hash
        return payload


def fixture_execution_request(
    permit: GovernedPermit,
    **overrides: Any,
) -> ExecutionRequest:
    candidate = ExecutionCandidate(
        candidate_id=overrides.get("candidate_id", "cand_fixture"),
        action_type=overrides.get("action_type", permit.requested_action_type),
        capability_id=overrides.get("capability_id", permit.capability_ref),
        effect_class=overrides.get("effect_class", permit.scope.effect_class),
    )
    chain = AuthorityChain(
        proposal_ref=overrides.get("proposal_ref", "prop_fixture"),
        hal_decision_ref=overrides.get("hal_decision_ref", "hal_dec_fixture"),
        soar_run_ref=overrides.get("soar_run_ref"),
        gpp_permit_id=permit.permit_id,
        gpp_permit_hash=permit.permit_hash,
    )
    rollback_required = overrides.get("rollback_required", candidate.effect_class == "external_write")
    return ExecutionRequest(
        request_id=overrides.get("request_id", f"ueak_req_{permit.request_id}"),
        candidate=candidate,
        authority_chain=chain,
        permit=overrides.get("permit", permit),
        identity_ref=overrides.get("identity_ref", permit.identity_ref),
        admission_ref=overrides.get("admission_ref", permit.admission_ref),
        freshness_ref=overrides.get("freshness_ref", permit.freshness_ref),
        approval_expires_at=overrides.get("approval_expires_at", permit.expires_at),
        redaction_ref=overrides.get("redaction_ref", permit.redaction_ref),
        retention_ref=overrides.get("retention_ref", permit.retention_ref),
        rollback=overrides.get(
            "rollback",
            RollbackRequirement(
                required=rollback_required,
                rollback_ref=overrides.get("rollback_ref", "rbk:fixture_1" if rollback_required else ""),
                compensation_ref=overrides.get("compensation_ref", ""),
            ),
        ),
        risk=overrides.get("risk", ExecutionRiskEnvelope()),
        panic_lockdown=overrides.get("panic_lockdown", False),
        redaction_payload=overrides.get("redaction_payload"),
        idempotency_key=overrides.get("idempotency_key", ""),
    )


__all__ = [
    "AdmissionStatus",
    "AuthorityChain",
    "EmergencyState",
    "ExecutionAdmissionDecision",
    "ExecutionCandidate",
    "ExecutionDispatchPlan",
    "ExecutionReceipt",
    "ExecutionRefusalReason",
    "ExecutionRequest",
    "ExecutionRiskEnvelope",
    "ExposureSurface",
    "PermitBinding",
    "ResourceGovernanceEnvelope",
    "RollbackRequirement",
    "fixture_execution_request",
]
