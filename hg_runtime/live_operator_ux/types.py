"""OUX-LIVE types — operator review console records are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.oux_live.errors import OuxValidationError
from hg_core.policy_safety.hashing import compute_record_hash

OUX_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T12:00:00.000000Z"

OperatorControlKind = Literal["approve", "deny", "revoke", "pause", "panic"]
APPROVAL_EVIDENCE_ACTIONS = frozenset({"approve"})
RESTRICT_ACTIONS = frozenset({"deny", "revoke", "pause", "panic"})

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
            raise OuxValidationError("oux.validation.secret", "secrets forbidden in OUX records")


@dataclass(frozen=True)
class OperatorSession:
    session_id: str
    operator_ref: str
    started_at: str
    freshness_ref: str
    approval_expires_at: str
    scope: str = "approve_change"
    session_status: str = "active"

    def __post_init__(self) -> None:
        _validate_no_secrets(self.session_id, self.operator_ref, self.freshness_ref, self.scope)
        if is_bare_operator_ref(self.operator_ref):
            raise OuxValidationError("oux.validation.bare_operator_ref", "IAM-bound operator ref required")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "oux-operator-session",
            "schema_version": OUX_SCHEMA_VERSION,
            "session_id": self.session_id,
            "operator_ref": self.operator_ref,
            "started_at": self.started_at,
            "freshness_ref": self.freshness_ref,
            "approval_expires_at": self.approval_expires_at,
            "scope": self.scope,
            "session_status": self.session_status,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class OperatorActionRequest:
    request_id: str
    review_item_ref: str
    control_kind: OperatorControlKind
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = False
    requires_ueak: bool = False
    treat_as_authority: bool = False
    ui_display_state: str | None = None
    silence_as_approval: bool = False
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.request_id,
            self.review_item_ref,
            str(self.operator_ref or ""),
            str(self.freshness_ref or ""),
            str(self.scope or ""),
            str(self.ui_display_state or ""),
        )
        if self.treat_as_authority:
            raise OuxValidationError("oux.validation.authority_created", "treat_as_authority forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "oux-operator-action-request",
            "schema_version": OUX_SCHEMA_VERSION,
            "request_id": self.request_id,
            "review_item_ref": self.review_item_ref,
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
        if self.scope:
            payload["scope"] = self.scope
        if self.gpp_permit_ref:
            payload["gpp_permit_ref"] = self.gpp_permit_ref
        if self.ueak_admission_ref:
            payload["ueak_admission_ref"] = self.ueak_admission_ref
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class OperatorUXReceipt:
    receipt_id: str
    request_id: str
    control_kind: OperatorControlKind
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    rollback_acknowledged: bool = False
    kill_switch_active: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.request_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "oux-operator-ux-receipt",
            "schema_version": OUX_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "control_kind": self.control_kind,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "rollback_acknowledged": self.rollback_acknowledged,
            "kill_switch_active": self.kill_switch_active,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class OperatorReviewQueueView:
    view_id: str
    item_count: int
    observed_at: str
    digest_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "oux-review-queue-view",
            "schema_version": OUX_SCHEMA_VERSION,
            "view_id": self.view_id,
            "item_count": self.item_count,
            "observed_at": self.observed_at,
            "digest_only": self.digest_only,
            "ui_state_is_not_authority": True,
            "permission_granted": False,
        }


@dataclass(frozen=True)
class OperatorUXAuditRecord:
    audit_id: str
    action_ref: str
    operator_ref: str | None
    observed_at: str
    event_code: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "oux-audit-record",
            "schema_version": OUX_SCHEMA_VERSION,
            "audit_id": self.audit_id,
            "action_ref": self.action_ref,
            "operator_ref": self.operator_ref,
            "observed_at": self.observed_at,
            "event_code": self.event_code,
            "permission_granted": False,
        }


def session_from_fixture(fixture: dict[str, Any]) -> OperatorSession:
    return OperatorSession(
        session_id=fixture["session_id"],
        operator_ref=fixture["operator_ref"],
        started_at=fixture.get("started_at", FIXTURE_CLOCK),
        freshness_ref=fixture.get("freshness_ref", "tim:approval_window_ok"),
        approval_expires_at=fixture.get("approval_expires_at", "2026-06-15T12:00:00.000000Z"),
        scope=fixture.get("scope", "approve_change"),
        session_status=fixture.get("session_status", "active"),
    )


def action_request_from_fixture(fixture: dict[str, Any]) -> OperatorActionRequest:
    return OperatorActionRequest(
        request_id=fixture["request_id"],
        review_item_ref=fixture.get("review_item_ref", "ori-item:fixture"),
        control_kind=fixture.get("control_kind", "approve"),  # type: ignore[arg-type]
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", False)),
        requires_ueak=bool(fixture.get("requires_ueak", False)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        ui_display_state=fixture.get("ui_display_state"),
        silence_as_approval=bool(fixture.get("silence_as_approval", False)),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "APPROVAL_EVIDENCE_ACTIONS",
    "FIXTURE_CLOCK",
    "OUX_SCHEMA_VERSION",
    "OperatorActionRequest",
    "OperatorControlKind",
    "OperatorReviewQueueView",
    "OperatorSession",
    "OperatorUXAuditRecord",
    "OperatorUXReceipt",
    "RESTRICT_ACTIONS",
    "action_request_from_fixture",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "session_from_fixture",
]
