"""ALOOP-LIVE types — loop leases are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.aloop_live.errors import AloopValidationError
from hg_core.policy_safety.hashing import compute_record_hash

ALOOP_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T15:00:00.000000Z"

LoopSupervisorState = Literal["pending", "supervised", "paused", "stopped", "denied"]

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
            raise AloopValidationError("aloop.validation.secret", "secrets forbidden in ALOOP records")


@dataclass(frozen=True)
class LoopLease:
    lease_id: str
    request_id: str
    loop_scope: str
    lease_expires_at: str
    heartbeat_ref: str
    budget_ref: str
    operator_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.lease_id,
            self.request_id,
            self.loop_scope,
            self.heartbeat_ref,
            self.budget_ref,
            str(self.operator_ref or ""),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aloop-lease",
            "schema_version": ALOOP_SCHEMA_VERSION,
            "lease_id": self.lease_id,
            "request_id": self.request_id,
            "loop_scope": self.loop_scope,
            "lease_expires_at": self.lease_expires_at,
            "heartbeat_ref": self.heartbeat_ref,
            "budget_ref": self.budget_ref,
            "authority_created": False,
            "permission_granted": False,
            "live_loop_started": False,
            "loop_self_renewed": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AutonomousLoopRequest:
    request_id: str
    loop_scope: str
    lease_expires_at: str
    heartbeat_ref: str
    budget_ref: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
    gpp_permit_ref: str | None = None
    ueak_admission_ref: str | None = None
    requires_gpp: bool = False
    requires_ueak: bool = False
    treat_as_authority: bool = False
    self_renewal_requested: bool = False
    rollback_plan_ref: str | None = None
    kill_switch_engaged: bool = False
    panic_lockdown: bool = False
    pause_requested: bool = False
    observed_at: str = FIXTURE_CLOCK

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.request_id,
            self.loop_scope,
            self.heartbeat_ref,
            self.budget_ref,
            str(self.operator_ref or ""),
            str(self.freshness_ref or ""),
            str(self.scope or ""),
            str(self.rollback_plan_ref or ""),
        )
        if self.treat_as_authority:
            raise AloopValidationError("aloop.validation.authority_created", "treat_as_authority forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aloop-loop-request",
            "schema_version": ALOOP_SCHEMA_VERSION,
            "request_id": self.request_id,
            "loop_scope": self.loop_scope,
            "lease_expires_at": self.lease_expires_at,
            "heartbeat_ref": self.heartbeat_ref,
            "budget_ref": self.budget_ref,
            "requires_gpp": self.requires_gpp,
            "requires_ueak": self.requires_ueak,
            "self_renewal_requested": self.self_renewal_requested,
            "kill_switch_engaged": self.kill_switch_engaged,
            "panic_lockdown": self.panic_lockdown,
            "pause_requested": self.pause_requested,
            "authority_created": False,
            "permission_granted": False,
            "live_loop_started": False,
            "loop_self_renewed": False,
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
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class LoopSupervisorReceipt:
    receipt_id: str
    request_id: str
    lease_id: str
    supervisor_state: LoopSupervisorState
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    rollback_acknowledged: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.request_id, self.lease_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aloop-supervisor-receipt",
            "schema_version": ALOOP_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "lease_id": self.lease_id,
            "supervisor_state": self.supervisor_state,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "rollback_acknowledged": self.rollback_acknowledged,
            "live_loop_started": False,
            "loop_self_renewed": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def request_from_fixture(fixture: dict[str, Any]) -> AutonomousLoopRequest:
    return AutonomousLoopRequest(
        request_id=fixture["request_id"],
        loop_scope=fixture.get("loop_scope", "loop:fixture:observe"),
        lease_expires_at=fixture.get("lease_expires_at", "2026-06-15T12:00:00.000000Z"),
        heartbeat_ref=fixture.get("heartbeat_ref", "hrt:heartbeat:fresh"),
        budget_ref=fixture.get("budget_ref", "budget:fixture:ok"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
        gpp_permit_ref=fixture.get("gpp_permit_ref"),
        ueak_admission_ref=fixture.get("ueak_admission_ref"),
        requires_gpp=bool(fixture.get("requires_gpp", False)),
        requires_ueak=bool(fixture.get("requires_ueak", False)),
        treat_as_authority=bool(fixture.get("treat_as_authority", False)),
        self_renewal_requested=bool(fixture.get("self_renewal_requested", False)),
        rollback_plan_ref=fixture.get("rollback_plan_ref"),
        kill_switch_engaged=bool(fixture.get("kill_switch_engaged", False)),
        panic_lockdown=bool(fixture.get("panic_lockdown", False)),
        pause_requested=bool(fixture.get("pause_requested", False)),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
    )


__all__ = [
    "ALOOP_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "AutonomousLoopRequest",
    "LoopLease",
    "LoopSupervisorReceipt",
    "LoopSupervisorState",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "request_from_fixture",
]
