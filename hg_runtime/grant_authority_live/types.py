"""GMG-LIVE types — grant candidates are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.gmg_live.errors import GmgValidationError
from hg_core.policy_safety.hashing import compute_record_hash

GMG_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T14:00:00.000000Z"

GrantType = Literal["tool", "memory_namespace", "context", "budget"]
GrantControlKind = Literal["issue", "revoke", "expire"]

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

_AMBIENT_SCOPE_MARKERS = frozenset({"*", "all", "global", "ambient", "any"})


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


def is_ambient_grant_scope(scope: str | None) -> bool:
    raw = str(scope or "").strip().lower()
    return raw in _AMBIENT_SCOPE_MARKERS


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise GmgValidationError("gmg.validation.secret", "secrets forbidden in GMG records")


def _grant_target_fields(grant_type: GrantType) -> tuple[str, ...]:
    return {
        "tool": ("tool_ref",),
        "memory_namespace": ("namespace_ref",),
        "context": ("context_scope",),
        "budget": ("budget_limit",),
    }[grant_type]


@dataclass(frozen=True)
class GrantCandidate:
    candidate_id: str
    request_id: str
    grant_type: GrantType
    grant_target: str
    operator_ref: str | None = None
    gpp_permit_ref: str | None = None
    rollback_plan_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.candidate_id,
            self.request_id,
            self.grant_type,
            self.grant_target,
            str(self.operator_ref or ""),
            str(self.gpp_permit_ref or ""),
            str(self.rollback_plan_ref or ""),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "gmg-grant-candidate",
            "schema_version": GMG_SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "request_id": self.request_id,
            "grant_type": self.grant_type,
            "grant_target": self.grant_target,
            "authority_created": False,
            "permission_granted": False,
            "is_permit": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.gpp_permit_ref:
            payload["gpp_permit_ref"] = self.gpp_permit_ref
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class GrantRequest:
    request_id: str
    grant_type: GrantType
    control_kind: GrantControlKind
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    grant_expires_at: str | None
    scope: str | None = None
    tool_ref: str | None = None
    namespace_ref: str | None = None
    context_scope: str | None = None
    budget_limit: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = False
    requires_ueak: bool = False
    treat_as_authority: bool = False
    rollback_plan_ref: str | None = None
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.request_id,
            str(self.operator_ref or ""),
            str(self.freshness_ref or ""),
            str(self.scope or ""),
            str(self.tool_ref or ""),
            str(self.namespace_ref or ""),
            str(self.context_scope or ""),
            str(self.budget_limit or ""),
            str(self.rollback_plan_ref or ""),
        )
        if self.treat_as_authority:
            raise GmgValidationError("gmg.validation.authority_created", "treat_as_authority forbidden")

    def grant_target(self) -> str | None:
        if self.grant_type == "tool":
            return self.tool_ref
        if self.grant_type == "memory_namespace":
            return self.namespace_ref
        if self.grant_type == "context":
            return self.context_scope
        if self.grant_type == "budget":
            return self.budget_limit
        return None

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "gmg-grant-request",
            "schema_version": GMG_SCHEMA_VERSION,
            "request_id": self.request_id,
            "grant_type": self.grant_type,
            "control_kind": self.control_kind,
            "requires_gpp": self.requires_gpp,
            "requires_ueak": self.requires_ueak,
            "authority_created": False,
            "permission_granted": False,
            "observed_at": self.observed_at,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.freshness_ref:
            payload["freshness_ref"] = self.freshness_ref
        if self.approval_expires_at:
            payload["approval_expires_at"] = self.approval_expires_at
        if self.grant_expires_at:
            payload["grant_expires_at"] = self.grant_expires_at
        if self.scope:
            payload["scope"] = self.scope
        if self.tool_ref:
            payload["tool_ref"] = self.tool_ref
        if self.namespace_ref:
            payload["namespace_ref"] = self.namespace_ref
        if self.context_scope:
            payload["context_scope"] = self.context_scope
        if self.budget_limit:
            payload["budget_limit"] = self.budget_limit
        if self.gpp_permit_ref:
            payload["gpp_permit_ref"] = self.gpp_permit_ref
        if self.ueak_admission_ref:
            payload["ueak_admission_ref"] = self.ueak_admission_ref
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class GrantReceipt:
    receipt_id: str
    request_id: str
    candidate_id: str
    grant_type: GrantType
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    permit_bound: bool = False
    revocation_available: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.request_id, self.candidate_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "gmg-grant-receipt",
            "schema_version": GMG_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "grant_type": self.grant_type,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "permit_bound": self.permit_bound,
            "revocation_available": self.revocation_available,
            "live_grant_performed": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class GrantRevocation:
    revocation_id: str
    receipt_id: str
    request_id: str
    grant_type: GrantType
    grant_target: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "gmg-grant-revocation",
            "schema_version": GMG_SCHEMA_VERSION,
            "revocation_id": self.revocation_id,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "grant_type": self.grant_type,
            "grant_target": self.grant_target,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_grant_performed": False,
        }


@dataclass(frozen=True)
class GrantExpiryRecord:
    expiry_id: str
    receipt_id: str
    grant_type: GrantType
    grant_target: str
    grant_expires_at: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "gmg-grant-expiry",
            "schema_version": GMG_SCHEMA_VERSION,
            "expiry_id": self.expiry_id,
            "receipt_id": self.receipt_id,
            "grant_type": self.grant_type,
            "grant_target": self.grant_target,
            "grant_expires_at": self.grant_expires_at,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_grant_performed": False,
        }


@dataclass(frozen=True)
class GrantAuditRecord:
    audit_id: str
    receipt_id: str
    request_id: str
    grant_type: GrantType
    reason_code: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "gmg-grant-audit",
            "schema_version": GMG_SCHEMA_VERSION,
            "audit_id": self.audit_id,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "grant_type": self.grant_type,
            "reason_code": self.reason_code,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_grant_performed": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> GrantRequest:
    return GrantRequest(
        request_id=fixture["request_id"],
        grant_type=fixture.get("grant_type", "tool"),  # type: ignore[arg-type]
        control_kind=fixture.get("control_kind", "issue"),  # type: ignore[arg-type]
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        grant_expires_at=fixture.get("grant_expires_at"),
        scope=fixture.get("scope"),
        tool_ref=fixture.get("tool_ref"),
        namespace_ref=fixture.get("namespace_ref"),
        context_scope=fixture.get("context_scope"),
        budget_limit=fixture.get("budget_limit"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", False)),
        requires_ueak=bool(fixture.get("requires_ueak", False)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        rollback_plan_ref=fixture.get("rollback_plan_ref"),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "GMG_SCHEMA_VERSION",
    "GrantAuditRecord",
    "GrantCandidate",
    "GrantControlKind",
    "GrantExpiryRecord",
    "GrantReceipt",
    "GrantRequest",
    "GrantRevocation",
    "GrantType",
    "is_ambient_grant_scope",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "request_from_fixture",
]
