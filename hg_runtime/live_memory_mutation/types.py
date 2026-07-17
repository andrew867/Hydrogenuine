"""MEM-LIVE types — memory write candidates are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.mem_live.errors import MemValidationError
from hg_core.policy_safety.hashing import compute_record_hash

MEM_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T13:00:00.000000Z"

MemoryMutationKind = Literal["write", "update", "delete", "restore"]

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
            raise MemValidationError("mem.validation.secret", "secrets forbidden in MEM records")


@dataclass(frozen=True)
class MemoryWriteCandidate:
    candidate_id: str
    request_id: str
    mutation_kind: MemoryMutationKind
    memory_key: str
    payload_digest: str
    operator_ref: str | None = None
    rollback_plan_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.candidate_id,
            self.request_id,
            self.memory_key,
            self.payload_digest,
            str(self.operator_ref or ""),
            str(self.rollback_plan_ref or ""),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mem-write-candidate",
            "schema_version": MEM_SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "request_id": self.request_id,
            "mutation_kind": self.mutation_kind,
            "memory_key": self.memory_key,
            "payload_digest": self.payload_digest,
            "authority_created": False,
            "permission_granted": False,
            "is_permit": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class MemoryMutationRequest:
    request_id: str
    mutation_kind: MemoryMutationKind
    memory_key: str
    payload_digest: str
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
            self.memory_key,
            self.payload_digest,
            str(self.operator_ref or ""),
            str(self.freshness_ref or ""),
            str(self.scope or ""),
            str(self.rollback_plan_ref or ""),
        )
        if self.treat_as_authority:
            raise MemValidationError("mem.validation.authority_created", "treat_as_authority forbidden")

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mem-mutation-request",
            "schema_version": MEM_SCHEMA_VERSION,
            "request_id": self.request_id,
            "mutation_kind": self.mutation_kind,
            "memory_key": self.memory_key,
            "payload_digest": self.payload_digest,
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
        if self.rollback_plan_ref:
            payload["rollback_plan_ref"] = self.rollback_plan_ref
        if include_hash:
            payload["record_hash"] = compute_record_hash(payload)
        return payload


@dataclass(frozen=True)
class MemoryMutationReceipt:
    receipt_id: str
    request_id: str
    candidate_id: str
    mutation_kind: MemoryMutationKind
    status: str
    reason_code: str
    operator_ref: str | None = None
    evidence_admissible: bool = False
    rollback_acknowledged: bool = False
    restore_available: bool = False
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.receipt_id, self.request_id, self.candidate_id, str(self.operator_ref or ""))
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mem-mutation-receipt",
            "schema_version": MEM_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "mutation_kind": self.mutation_kind,
            "status": self.status,
            "reason_code": self.reason_code,
            "authority_created": False,
            "permission_granted": False,
            "evidence_admissible": self.evidence_admissible,
            "rollback_acknowledged": self.rollback_acknowledged,
            "restore_available": self.restore_available,
            "durable_write_performed": False,
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
    memory_key: str
    prior_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "mem-rollback-record",
            "schema_version": MEM_SCHEMA_VERSION,
            "rollback_id": self.rollback_id,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "memory_key": self.memory_key,
            "prior_digest": self.prior_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "durable_write_performed": False,
        }


@dataclass(frozen=True)
class RestoreRecord:
    restore_id: str
    rollback_id: str
    memory_key: str
    restored_digest: str
    observed_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "mem-restore-record",
            "schema_version": MEM_SCHEMA_VERSION,
            "restore_id": self.restore_id,
            "rollback_id": self.rollback_id,
            "memory_key": self.memory_key,
            "restored_digest": self.restored_digest,
            "observed_at": self.observed_at,
            "permission_granted": False,
            "authority_created": False,
            "durable_write_performed": False,
        }


def request_from_fixture(fixture: dict[str, Any]) -> MemoryMutationRequest:
    return MemoryMutationRequest(
        request_id=fixture["request_id"],
        mutation_kind=fixture.get("mutation_kind", "write"),  # type: ignore[arg-type]
        memory_key=fixture.get("memory_key", "mem:fixture:key"),
        payload_digest=fixture.get("payload_digest", "digest:fixture"),
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
    "MEM_SCHEMA_VERSION",
    "MemoryMutationKind",
    "MemoryMutationReceipt",
    "MemoryMutationRequest",
    "MemoryWriteCandidate",
    "RestoreRecord",
    "RollbackRecord",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "request_from_fixture",
]
