"""SRP-LIVE types — SRP apply plans are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.srp_live.errors import SrpValidationError
from hg_core.policy_safety.hashing import compute_record_hash

SRP_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T14:00:00.000000Z"

ApplyPhase = Literal["plan", "apply"]

_STALE_TIM_REFS = frozenset({"tim:missing", "freshness:missing", "tim:stale"})
_VALID_TIM_PREFIXES = ("tim:approval_window_ok", "tim:fresh:")

_BARE_PLACEHOLDER_REFS = frozenset(
    {
        "",
        "operator",
        "operator_id",
        "human",
        "user",
        "admin",
        "TBD",
        "unknown",
        "placeholder",
    }
)


def is_bare_operator_ref(operator_ref: str | None) -> bool:
    raw = str(operator_ref or "").strip()
    if not raw:
        return True
    if raw in _BARE_PLACEHOLDER_REFS:
        return True
    if ":" not in raw and not raw.startswith("op:"):
        return True
    return False


def is_valid_tim_freshness(freshness_ref: str | None) -> bool:
    raw = str(freshness_ref or "").strip()
    if not raw or raw in _STALE_TIM_REFS:
        return False
    return any(raw.startswith(prefix) for prefix in _VALID_TIM_PREFIXES)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise SrpValidationError("srp.validation.secret", "secrets forbidden in SRP records")


@dataclass(frozen=True)
class SRPApplyRequest:
    repair_id: str
    target_ref: str
    change_set_digest: str
    approved_digest: str
    sandbox_proof_ref: str
    approval_receipt_ref: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    tep_envelope_ref: str | None = None
    rollback_plan_ref: str | None = None
    scope: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    idempotency_key: str | None = None
    self_approved: bool = False
    treat_as_authority: bool = False
    irreversible_step: bool = False
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.repair_id,
            self.target_ref,
            self.change_set_digest,
            self.approved_digest,
            str(self.operator_ref or ""),
            str(self.sandbox_proof_ref or ""),
            str(self.approval_receipt_ref or ""),
        )
        if self.treat_as_authority:
            raise SrpValidationError("srp.validation.authority_created", "treat_as_authority forbidden")
        if self.self_approved:
            raise SrpValidationError("srp.validation.self_modification", "self_approved forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "srp-apply-request",
            "schema_version": SRP_SCHEMA_VERSION,
            "repair_id": self.repair_id,
            "target_ref": self.target_ref,
            "change_set_digest": self.change_set_digest,
            "approved_digest": self.approved_digest,
            "sandbox_proof_ref": self.sandbox_proof_ref,
            "approval_receipt_ref": self.approval_receipt_ref,
            "authority_created": False,
            "permission_granted": False,
            "srp_apply_called": False,
            "live_landing_performed": False,
            "observed_at": self.observed_at,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.freshness_ref:
            payload["freshness_ref"] = self.freshness_ref
        if self.approval_expires_at:
            payload["approval_expires_at"] = self.approval_expires_at
        if self.tep_envelope_ref:
            payload["tep_envelope_ref"] = self.tep_envelope_ref
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if self.scope:
            payload["scope"] = self.scope
        if self.gpp_permit_ref:
            payload["gpp_permit_ref"] = self.gpp_permit_ref
        if self.ueak_admission_ref:
            payload["ueak_admission_ref"] = self.ueak_admission_ref
        if self.idempotency_key:
            payload["idempotency_key"] = self.idempotency_key
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class SRPApplyPermitBinding:
    binding_id: str
    repair_id: str
    gpp_permit_ref: str | None
    ueak_admission_ref: str | None
    expired: bool = False
    revoked: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "srp-apply-permit-binding",
            "schema_version": SRP_SCHEMA_VERSION,
            "binding_id": self.binding_id,
            "repair_id": self.repair_id,
            "gpp_permit_ref": self.gpp_permit_ref,
            "ueak_admission_ref": self.ueak_admission_ref,
            "expired": self.expired,
            "revoked": self.revoked,
            "gpp_permit_minted": False,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SRPApplyPlan:
    plan_id: str
    repair_id: str
    phase: ApplyPhase
    pre_checks: tuple[str, ...]
    apply_steps: tuple[str, ...]
    verify_steps: tuple[str, ...]
    abort_points: tuple[str, ...]
    operator_visible: bool = True
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "srp-apply-plan",
            "schema_version": SRP_SCHEMA_VERSION,
            "plan_id": self.plan_id,
            "repair_id": self.repair_id,
            "phase": self.phase,
            "pre_checks": list(self.pre_checks),
            "apply_steps": list(self.apply_steps),
            "verify_steps": list(self.verify_steps),
            "abort_points": list(self.abort_points),
            "operator_visible": self.operator_visible,
            "srp_apply_called": False,
            "live_landing_performed": False,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SRPApplyReceipt:
    receipt_id: str
    repair_id: str
    outcome: str
    permit_ref: str | None
    admission_ref: str | None
    approved_digest: str
    applied_digest: str
    sandbox_proof_ref: str
    rollback_refs: tuple[str, ...] = ()
    audit_ref: str | None = None
    operator_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.repair_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "srp-apply-receipt",
            "schema_version": SRP_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "repair_id": self.repair_id,
            "outcome": self.outcome,
            "approved_digest": self.approved_digest,
            "applied_digest": self.applied_digest,
            "sandbox_proof_ref": self.sandbox_proof_ref,
            "rollback_refs": list(self.rollback_refs),
            "live_landing_performed": False,
            "srp_apply_called": False,
            "gpp_permit_minted": False,
            "authority_created": False,
            "permission_granted": False,
        }
        if self.permit_ref:
            payload["permit_ref"] = self.permit_ref
        if self.admission_ref:
            payload["admission_ref"] = self.admission_ref
        if self.audit_ref:
            payload["audit_ref"] = self.audit_ref
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SRPApplyRollbackPlan:
    rollback_plan_id: str
    repair_id: str
    reversible_steps: tuple[str, ...]
    irreversible_steps: tuple[str, ...]
    irreversible_ack_required: bool = False
    compensation_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "srp-apply-rollback-plan",
            "schema_version": SRP_SCHEMA_VERSION,
            "rollback_plan_id": self.rollback_plan_id,
            "repair_id": self.repair_id,
            "reversible_steps": list(self.reversible_steps),
            "irreversible_steps": list(self.irreversible_steps),
            "irreversible_ack_required": self.irreversible_ack_required,
            "compensation_ref": self.compensation_ref,
            "live_landing_performed": False,
            "authority_created": False,
        }


@dataclass(frozen=True)
class SRPApplyAuditRecord:
    audit_id: str
    repair_id: str
    request_ref: str
    permit_binding_ref: str | None
    admission_ref: str | None
    plan_ref: str | None
    receipt_ref: str | None
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "srp-apply-audit-record",
            "schema_version": SRP_SCHEMA_VERSION,
            "audit_id": self.audit_id,
            "repair_id": self.repair_id,
            "request_ref": self.request_ref,
            "permit_binding_ref": self.permit_binding_ref,
            "admission_ref": self.admission_ref,
            "plan_ref": self.plan_ref,
            "receipt_ref": self.receipt_ref,
            "observed_at": self.observed_at,
            "authority_created": False,
            "srp_apply_called": False,
        }


@dataclass(frozen=True)
class RollbackRecord:
    rollback_id: str
    receipt_id: str
    repair_id: str
    target_ref: str
    prior_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "srp-rollback-record",
            "schema_version": SRP_SCHEMA_VERSION,
            "rollback_id": self.rollback_id,
            "receipt_id": self.receipt_id,
            "repair_id": self.repair_id,
            "target_ref": self.target_ref,
            "prior_digest": self.prior_digest,
            "observed_at": self.observed_at,
            "live_landing_performed": False,
            "authority_created": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> SRPApplyRequest:
    return SRPApplyRequest(
        repair_id=fixture["repair_id"],
        target_ref=fixture.get("target_ref", "target:fixture"),
        change_set_digest=fixture.get("change_set_digest", fixture.get("approved_digest", "digest:fixture")),
        approved_digest=fixture.get("approved_digest", "digest:fixture"),
        sandbox_proof_ref=fixture.get("sandbox_proof_ref", "sandbox:proof:fixture"),
        approval_receipt_ref=fixture.get("approval_receipt_ref", "approval:receipt:fixture"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        tep_envelope_ref=fixture.get("tep_envelope_ref"),
        rollback_plan_ref=fixture.get("rollback_plan_ref"),
        scope=fixture.get("scope"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        idempotency_key=fixture.get("idempotency_key"),
        self_approved=bool(fixture.get("self_approved", False)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        irreversible_step=bool(fixture.get("irreversible_step", False)),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


def permit_binding_from_fixture(fixture: dict[str, Any] | None) -> SRPApplyPermitBinding | None:
    if not fixture:
        return None
    return SRPApplyPermitBinding(
        binding_id=fixture.get("binding_id", f"bind:{fixture.get('repair_id', 'unknown')}"),
        repair_id=fixture.get("repair_id", ""),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        expired=bool(fixture.get("expired", False)),
        revoked=bool(fixture.get("revoked", False)),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "SRP_SCHEMA_VERSION",
    "ApplyPhase",
    "RollbackRecord",
    "SRPApplyAuditRecord",
    "SRPApplyPermitBinding",
    "SRPApplyPlan",
    "SRPApplyReceipt",
    "SRPApplyRequest",
    "SRPApplyRollbackPlan",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "permit_binding_from_fixture",
    "request_from_fixture",
]
