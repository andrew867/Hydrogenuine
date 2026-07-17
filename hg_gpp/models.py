"""GPP permit authority models — grant/deny evidence only; no execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Sequence, Union

from hg_core.governance.canonical_hash import canonical_hash

GPP_PERMIT_SCHEMA = "gpp-governed-permit"
GPP_PERMIT_SCHEMA_VERSION = "1.0"
GPP_RECEIPT_SCHEMA = "gpp-permit-receipt"
GPP_RECEIPT_SCHEMA_VERSION = "1.0"

PermitStatus = Literal["granted", "denied", "expired", "revoked", "invalid"]
PermitKind = Literal["publish", "execute"]


@dataclass(frozen=True)
class PermitDenyReason:
    code: str
    detail: str = ""

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class PermitEvidenceRef:
    ref_id: str
    kind: str = "evidence"

    def to_payload(self) -> dict[str, str]:
        return {"ref_id": self.ref_id, "kind": self.kind}


@dataclass(frozen=True)
class PermitScope:
    capability_ref: str
    effect_class: str
    requested_action_type: str
    allowed_actions: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "capability_ref": self.capability_ref,
            "effect_class": self.effect_class,
            "requested_action_type": self.requested_action_type,
            "allowed_actions": list(self.allowed_actions),
        }

    def matches(self, *, capability_ref: str, effect_class: str, action_type: str) -> bool:
        if self.capability_ref != capability_ref or self.effect_class != effect_class:
            return False
        if self.allowed_actions and action_type not in self.allowed_actions:
            return False
        return self.requested_action_type == action_type or action_type in self.allowed_actions


@dataclass(frozen=True)
class PermitRequest:
    request_id: str
    subject_id: str
    agent_id: str
    requested_action_type: str
    scope: PermitScope
    evidence_refs: tuple[PermitEvidenceRef, ...]
    proof_bundle_refs: tuple[str, ...]
    identity_ref: str
    admission_ref: str
    freshness_ref: str
    redaction_ref: str
    retention_ref: str
    capability_ref: str
    risk_class: str
    authority_chain_ref: str
    operator_ref: Optional[str] = None
    approval_expires_at: Optional[str] = None
    requestor_id: Optional[str] = None
    permit_kind: PermitKind = "execute"
    redaction_payload: Optional[dict[str, Any]] = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "gpp-permit-request",
            "schema_version": "1.0",
            "request_id": self.request_id,
            "subject_id": self.subject_id,
            "agent_id": self.agent_id,
            "operator_ref": self.operator_ref,
            "authority_chain_ref": self.authority_chain_ref,
            "requested_action_type": self.requested_action_type,
            "scope": self.scope.to_payload(),
            "evidence_refs": [e.to_payload() for e in self.evidence_refs],
            "proof_bundle_refs": list(self.proof_bundle_refs),
            "identity_ref": self.identity_ref,
            "admission_ref": self.admission_ref,
            "freshness_ref": self.freshness_ref,
            "redaction_ref": self.redaction_ref,
            "retention_ref": self.retention_ref,
            "capability_ref": self.capability_ref,
            "risk_class": self.risk_class,
            "approval_expires_at": self.approval_expires_at,
            "permit_kind": self.permit_kind,
        }


@dataclass(frozen=True)
class GovernedPermit:
    """Full governed permit — GPP mints; UEAK consumes."""

    permit_id: str
    request_id: str
    subject_id: str
    agent_id: str
    operator_ref: Optional[str]
    authority_chain_ref: str
    requested_action_type: str
    scope: PermitScope
    evidence_refs: tuple[PermitEvidenceRef, ...]
    proof_bundle_refs: tuple[str, ...]
    identity_ref: str
    admission_ref: str
    freshness_ref: str
    redaction_ref: str
    retention_ref: str
    capability_ref: str
    risk_class: str
    issued_at: str
    expires_at: str
    status: PermitStatus
    deny_reasons: tuple[PermitDenyReason, ...]
    revoked_at: Optional[str] = None
    permit_kind: PermitKind = "execute"
    permit_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "permit_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": GPP_PERMIT_SCHEMA,
            "schema_version": GPP_PERMIT_SCHEMA_VERSION,
            "permit_id": self.permit_id,
            "request_id": self.request_id,
            "subject_id": self.subject_id,
            "agent_id": self.agent_id,
            "operator_ref": self.operator_ref,
            "authority_chain_ref": self.authority_chain_ref,
            "requested_action_type": self.requested_action_type,
            "scope": self.scope.to_payload(),
            "evidence_refs": [e.to_payload() for e in self.evidence_refs],
            "proof_bundle_refs": list(self.proof_bundle_refs),
            "identity_ref": self.identity_ref,
            "admission_ref": self.admission_ref,
            "freshness_ref": self.freshness_ref,
            "redaction_ref": self.redaction_ref,
            "retention_ref": self.retention_ref,
            "capability_ref": self.capability_ref,
            "risk_class": self.risk_class,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "status": self.status,
            "deny_reasons": [r.to_payload() for r in self.deny_reasons],
            "permit_kind": self.permit_kind,
        }
        if include_hash:
            payload["permit_hash"] = self.permit_hash
        return payload


PublishPermit = GovernedPermit
ExecutionPermit = GovernedPermit


@dataclass(frozen=True)
class PermitDecision:
    status: PermitStatus
    permit: Optional[GovernedPermit] = None
    deny_reasons: tuple[PermitDenyReason, ...] = ()
    receipt: Optional["PermitReceipt"] = None


@dataclass(frozen=True)
class PermitReceipt:
    receipt_id: str
    permit_id: str
    request_id: str
    status: PermitStatus
    issued_at: str
    permit_hash: str
    receipt_hash: str = field(init=False)

    def __post_init__(self) -> None:
        body = {
            "schema": GPP_RECEIPT_SCHEMA,
            "schema_version": GPP_RECEIPT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "permit_id": self.permit_id,
            "request_id": self.request_id,
            "status": self.status,
            "issued_at": self.issued_at,
            "permit_hash": self.permit_hash,
        }
        object.__setattr__(self, "receipt_hash", canonical_hash(body))

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": GPP_RECEIPT_SCHEMA,
            "schema_version": GPP_RECEIPT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "permit_id": self.permit_id,
            "request_id": self.request_id,
            "status": self.status,
            "issued_at": self.issued_at,
            "permit_hash": self.permit_hash,
            "receipt_hash": self.receipt_hash,
        }


@dataclass(frozen=True)
class PermitRevocation:
    permit_id: str
    revoked_at: str
    reason_code: str
    revoker_ref: str

    def to_payload(self) -> dict[str, str]:
        return {
            "permit_id": self.permit_id,
            "revoked_at": self.revoked_at,
            "reason_code": self.reason_code,
            "revoker_ref": self.revoker_ref,
        }


class PermitVerifier:
    """Verifies governed permits — no execution side effects."""

    def verify(
        self,
        permit: GovernedPermit,
        *,
        now: str,
        store: Any,
        action_type: Optional[str] = None,
        capability_ref: Optional[str] = None,
        effect_class: Optional[str] = None,
    ) -> tuple[bool, str]:
        from hg_gpp.verifier import verify_permit

        return verify_permit(
            permit,
            now=now,
            store=store,
            action_type=action_type,
            capability_ref=capability_ref,
            effect_class=effect_class,
        )


def fixture_permit_request(**overrides: Any) -> PermitRequest:
    """Valid fixture request for tests and binder bridge."""
    cap_ref = overrides.get("capability_ref", "cap.oea_stub_log")
    effect = overrides.get("effect_class", "audit_log")
    action = overrides.get("requested_action_type", "oea_stub_log")
    scope = overrides.get(
        "scope",
        PermitScope(
            capability_ref=cap_ref,
            effect_class=effect,
            requested_action_type=action,
            allowed_actions=(action,),
        ),
    )
    base = PermitRequest(
        request_id=overrides.get("request_id", "gpp_req_fixture"),
        subject_id=overrides.get("subject_id", "subject:fixture"),
        agent_id=overrides.get("agent_id", "agent:fixture"),
        requested_action_type=scope.requested_action_type,
        scope=scope,
        evidence_refs=overrides.get(
            "evidence_refs",
            (PermitEvidenceRef("ev:decision_trace", "decision"),),
        ),
        proof_bundle_refs=overrides.get("proof_bundle_refs", ("proof:fixture_bundle",)),
        identity_ref=overrides.get("identity_ref", "op:local"),
        admission_ref=overrides.get("admission_ref", "adm:token_fixture_valid"),
        freshness_ref=overrides.get("freshness_ref", "tim:approval_window_ok"),
        redaction_ref=overrides.get("redaction_ref", "sec:redaction_passed"),
        retention_ref=overrides.get("retention_ref", "ret:bundle_fixture_1"),
        capability_ref=scope.capability_ref,
        risk_class=overrides.get("risk_class", "low"),
        authority_chain_ref=overrides.get("authority_chain_ref", "dec_allow_stub"),
        operator_ref=overrides.get("operator_ref", "op:local"),
        approval_expires_at=overrides.get("approval_expires_at", "2099-12-31T23:59:59.000000Z"),
        requestor_id=overrides.get("requestor_id", "agent:fixture"),
        permit_kind=overrides.get("permit_kind", "execute"),
        redaction_payload=overrides.get("redaction_payload"),
    )
    return base


__all__ = [
    "ExecutionPermit",
    "GovernedPermit",
    "PermitDecision",
    "PermitDenyReason",
    "PermitEvidenceRef",
    "PermitKind",
    "PermitReceipt",
    "PermitRequest",
    "PermitRevocation",
    "PermitScope",
    "PermitStatus",
    "PermitVerifier",
    "PublishPermit",
    "fixture_permit_request",
]
