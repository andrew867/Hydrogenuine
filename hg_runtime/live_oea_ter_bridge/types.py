"""OEA-TER-LIVE types — dispatch candidates are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.oea_ter_live.errors import OeaTerValidationError
from hg_core.policy_safety.hashing import compute_record_hash

OEA_TER_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T15:00:00.000000Z"

ExternalSurface = Literal["fake", "shell", "http", "fs", "process", "actuator", "tool_runtime"]
ActionControlKind = Literal["dispatch", "rollback", "compensate", "panic"]

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
            raise OeaTerValidationError("oea_ter.validation.secret", "secrets forbidden in OEA-TER records")


@dataclass(frozen=True)
class LiveActionCandidate:
    candidate_id: str
    request_id: str
    external_surface: ExternalSurface
    action_digest: str
    operator_ref: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    rollback_plan_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.candidate_id,
            self.request_id,
            self.external_surface,
            self.action_digest,
            str(self.operator_ref or ""),
            str(self.gpp_permit_ref or ""),
            str(self.ueak_admission_ref or ""),
            str(self.rollback_plan_ref or ""),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "oea-ter-dispatch-candidate",
            "schema_version": OEA_TER_SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "request_id": self.request_id,
            "external_surface": self.external_surface,
            "action_digest": self.action_digest,
            "authority_created": False,
            "permission_granted": False,
            "is_permit": False,
            "oea_ter_called": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.gpp_permit_ref:
            payload["gpp_permit_ref"] = self.gpp_permit_ref
        if self.ueak_admission_ref:
            payload["ueak_admission_ref"] = self.ueak_admission_ref
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class LiveActionRequest:
    request_id: str
    external_surface: ExternalSurface
    action_digest: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = True
    requires_ueak: bool = True
    treat_as_authority: bool = False
    rollback_plan_ref: str | None = None
    compensation_plan_ref: str | None = None
    control_kind: ActionControlKind = "dispatch"
    kill_switch_active: bool = False
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.request_id,
            self.external_surface,
            self.action_digest,
            str(self.operator_ref or ""),
            str(self.freshness_ref or ""),
            str(self.scope or ""),
            str(self.rollback_plan_ref or ""),
            str(self.compensation_plan_ref or ""),
        )
        if self.treat_as_authority:
            raise OeaTerValidationError("oea_ter.validation.authority_created", "treat_as_authority forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "oea-ter-dispatch-request",
            "schema_version": OEA_TER_SCHEMA_VERSION,
            "request_id": self.request_id,
            "external_surface": self.external_surface,
            "action_digest": self.action_digest,
            "control_kind": self.control_kind,
            "requires_gpp": self.requires_gpp,
            "requires_ueak": self.requires_ueak,
            "kill_switch_active": self.kill_switch_active,
            "authority_created": False,
            "permission_granted": False,
            "oea_ter_called": False,
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
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if self.compensation_plan_ref:
            payload["compensation_plan_ref"] = self.compensation_plan_ref
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class LiveActionReceipt:
    receipt_id: str
    request_id: str
    candidate_id: str
    external_surface: ExternalSurface
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    permit_bound: bool = False
    admission_bound: bool = False
    rollback_acknowledged: bool = False
    compensation_available: bool = False
    kill_switch_active: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.request_id, self.candidate_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "oea-ter-dispatch-receipt",
            "schema_version": OEA_TER_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "external_surface": self.external_surface,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "permit_bound": self.permit_bound,
            "admission_bound": self.admission_bound,
            "rollback_acknowledged": self.rollback_acknowledged,
            "compensation_available": self.compensation_available,
            "kill_switch_active": self.kill_switch_active,
            "live_action_performed": False,
            "oea_ter_called": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RollbackRecord:
    rollback_id: str
    receipt_id: str
    request_id: str
    action_digest: str
    prior_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "oea-ter-rollback-record",
            "schema_version": OEA_TER_SCHEMA_VERSION,
            "rollback_id": self.rollback_id,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "action_digest": self.action_digest,
            "prior_digest": self.prior_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_action_performed": False,
            "oea_ter_called": False,
        }


@dataclass(frozen=True)
class CompensationRecord:
    compensation_id: str
    rollback_id: str
    action_digest: str
    compensation_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "oea-ter-compensation-record",
            "schema_version": OEA_TER_SCHEMA_VERSION,
            "compensation_id": self.compensation_id,
            "rollback_id": self.rollback_id,
            "action_digest": self.action_digest,
            "compensation_digest": self.compensation_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_action_performed": False,
            "oea_ter_called": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> LiveActionRequest:
    control_kind = fixture.get("control_kind", "dispatch")
    return LiveActionRequest(
        request_id=fixture["request_id"],
        external_surface=fixture.get("external_surface", "fake"),  # type: ignore[arg-type]
        action_digest=fixture.get("action_digest", "digest:fixture"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", True)),
        requires_ueak=bool(fixture.get("requires_ueak", True)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        rollback_plan_ref=fixture.get("rollback_plan_ref"),
        compensation_plan_ref=fixture.get("compensation_plan_ref"),
        control_kind=control_kind,  # type: ignore[arg-type]
        kill_switch_active=bool(fixture.get("kill_switch_active", False)) or control_kind == "panic",
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "OEA_TER_SCHEMA_VERSION",
    "ActionControlKind",
    "CompensationRecord",
    "ExternalSurface",
    "LiveActionCandidate",
    "LiveActionReceipt",
    "LiveActionRequest",
    "RollbackRecord",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "request_from_fixture",
]
