"""RIB-SPAWN-LIVE types — spawn plans are not authority; child inherits nothing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.rib_spawn_live.errors import RibSpawnValidationError

RIB_SPAWN_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T14:00:00.000000Z"

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


def child_identity_distinct(parent_iam_ref: str, child_iam_ref: str) -> bool:
    return bool(parent_iam_ref) and bool(child_iam_ref) and parent_iam_ref != child_iam_ref


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise RibSpawnValidationError("rib_spawn.validation.secret", "secrets forbidden in RIB-SPAWN records")


@dataclass(frozen=True)
class ChildIdentityProfile:
    child_iam_ref: str
    parent_iam_ref: str
    inherits_permit: bool = False
    inherits_grant: bool = False
    inherits_memory: bool = False
    inherits_context: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.child_iam_ref, self.parent_iam_ref)
        if self.inherits_permit or self.inherits_grant or self.inherits_memory or self.inherits_context:
            raise RibSpawnValidationError(
                "rib_spawn.validation.inherited_authority",
                "child cannot inherit parent authority",
            )
        if not child_identity_distinct(self.parent_iam_ref, self.child_iam_ref):
            raise RibSpawnValidationError(
                "rib_spawn.validation.child_identity_collision",
                "child IAM must be distinct from parent",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-child-identity-profile",
            "schema_version": RIB_SPAWN_SCHEMA_VERSION,
            "child_iam_ref": self.child_iam_ref,
            "parent_iam_ref": self.parent_iam_ref,
            "inherits_permit": False,
            "inherits_grant": False,
            "inherits_memory": False,
            "inherits_context": False,
            "authority_created": False,
            "permission_granted": False,
            "child_inherits_authority": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ChildSpawnRequest:
    request_id: str
    parent_iam_ref: str
    child_iam_ref: str
    bootstrap_digest: str
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None = None
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
            self.parent_iam_ref,
            self.child_iam_ref,
            self.bootstrap_digest,
            str(self.operator_ref or ""),
            str(self.freshness_ref or ""),
            str(self.scope or ""),
            str(self.rollback_plan_ref or ""),
        )
        if self.treat_as_authority:
            raise RibSpawnValidationError("rib_spawn.validation.authority_created", "treat_as_authority forbidden")
        if not child_identity_distinct(self.parent_iam_ref, self.child_iam_ref):
            raise RibSpawnValidationError(
                "rib_spawn.validation.child_identity_collision",
                "child IAM must be distinct from parent",
            )

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-spawn-request",
            "schema_version": RIB_SPAWN_SCHEMA_VERSION,
            "request_id": self.request_id,
            "parent_iam_ref": self.parent_iam_ref,
            "child_iam_ref": self.child_iam_ref,
            "bootstrap_digest": self.bootstrap_digest,
            "requires_gpp": self.requires_gpp,
            "requires_ueak": self.requires_ueak,
            "authority_created": False,
            "permission_granted": False,
            "live_spawn_performed": False,
            "child_inherits_authority": False,
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
class ChildSpawnReceipt:
    receipt_id: str
    request_id: str
    child_iam_ref: str
    parent_iam_ref: str
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    rollback_acknowledged: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.receipt_id,
            self.request_id,
            self.child_iam_ref,
            self.parent_iam_ref,
            str(self.operator_ref or ""),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rib-spawn-receipt",
            "schema_version": RIB_SPAWN_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "child_iam_ref": self.child_iam_ref,
            "parent_iam_ref": self.parent_iam_ref,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "rollback_acknowledged": self.rollback_acknowledged,
            "live_spawn_performed": False,
            "child_inherits_authority": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class FailedSpawnRecord:
    failed_spawn_id: str
    request_id: str
    reason_code: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "rib-failed-spawn-record",
            "schema_version": RIB_SPAWN_SCHEMA_VERSION,
            "failed_spawn_id": self.failed_spawn_id,
            "request_id": self.request_id,
            "reason_code": self.reason_code,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "live_spawn_performed": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> ChildSpawnRequest:
    return ChildSpawnRequest(
        request_id=fixture["request_id"],
        parent_iam_ref=fixture.get("parent_iam_ref", "iam:parent:fixture"),
        child_iam_ref=fixture.get("child_iam_ref", "iam:child:fixture-distinct"),
        bootstrap_digest=fixture.get("bootstrap_digest", "digest:fixture-bootstrap"),
        operator_ref=fixture.get("operator_ref"),
        freshness_ref=fixture.get("freshness_ref"),
        approval_expires_at=fixture.get("approval_expires_at"),
        scope=fixture.get("scope"),
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
    "RIB_SPAWN_SCHEMA_VERSION",
    "ChildIdentityProfile",
    "ChildSpawnReceipt",
    "ChildSpawnRequest",
    "FailedSpawnRecord",
    "child_identity_distinct",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "request_from_fixture",
]
