"""BRS types — Bus Rate Supervisor is not authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.brs_cluster.errors import BrsValidationError
from hg_core.policy_safety.hashing import compute_record_hash

BRS_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T22:30:00.000000Z"

_FORBIDDEN_CLAIM = (
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "srp apply",
    "self-authorize",
    "treat as approved",
)


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise BrsValidationError("brs.validation.secret", "secrets forbidden in BRS records")


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise BrsValidationError("brs.validation.authority_created", f"{label} must not set authority_created=true")


def classify_brs_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "pressure grants token budget" in lower:
        return "token_grant"
    if "grant more context under pressure" in lower:
        return "context_grant"
    if "approve execution under pressure" in lower:
        return "execution_admission"
    if "bypasses resource governance" in lower:
        return "resource_bypass"
    if "mint gpp permit from bus signal" in lower:
        return "authority_conversion"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "authority_conversion"
    return None


@dataclass(frozen=True)
class RateSupervisorRecord:
    record_id: str
    summary: str
    observed_at: str
    classification: str = "unknown"
    authority_created: bool = False
    permission_granted: bool = False

    def __post_init__(self) -> None:
        _validate_no_secrets(self.record_id, self.summary)
        _reject_authority_created(self.authority_created, label="RateSupervisorRecord")
        if self.permission_granted:
            raise BrsValidationError("brs.validation.permission_granted", "BRS must not grant permission")
        if not self.record_id.startswith("brs:"):
            raise BrsValidationError("brs.validation.record_id", "record_id must start with brs:")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": BRS_SCHEMA_VERSION,
            "record_id": self.record_id,
            "summary": self.summary,
            "observed_at": self.observed_at,
            "classification": self.classification,
            "authority_created": False,
            "permission_granted": False,
            "rate_is_advisory_only": True,
            "proposal_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RatePressureSignal:
    signal_id: str
    pressure_score: float
    observed_at: str
    signal_summary: str = ""
    authority_created: bool = False
    permission_granted: bool = False

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="RatePressureSignal")
        if self.permission_granted:
            raise BrsValidationError("brs.validation.permission_granted", "signal must not grant permission")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": BRS_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "pressure_score": self.pressure_score,
            "observed_at": self.observed_at,
            "signal_summary": self.signal_summary,
            "authority_created": False,
            "permission_granted": False,
            "rate_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RateSupervisorReceipt:
    receipt_id: str
    record_ref: str
    emitted_events: tuple[str, ...]
    authority_created: bool = False
    permission_granted: bool = False
    permit_minted: bool = False
    execution_admitted: bool = False
    memory_history_mutated: bool = False
    deletion_performed: bool = False
    tool_removed: bool = False
    agent_spawned: bool = False
    oea_ter_called: bool = False

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="RateSupervisorReceipt")
        for flag, label in (
            (self.permission_granted, "permission_granted"),
            (self.permit_minted, "permit_minted"),
            (self.execution_admitted, "execution_admitted"),
            (self.memory_history_mutated, "memory_history_mutated"),
            (self.deletion_performed, "deletion_performed"),
            (self.tool_removed, "tool_removed"),
            (self.agent_spawned, "agent_spawned"),
            (self.oea_ter_called, "oea_ter_called"),
        ):
            if flag:
                raise BrsValidationError(f"brs.validation.{label}", f"{label} must remain false")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": BRS_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "record_ref": self.record_ref,
            "emitted_events": list(self.emitted_events),
            "authority_created": False,
            "permission_granted": False,
            "permit_minted": False,
            "execution_admitted": False,
            "memory_history_mutated": False,
            "deletion_performed": False,
            "tool_removed": False,
            "agent_spawned": False,
            "oea_ter_called": False,
            "rate_is_advisory_only": True,
            "proposal_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in ("authority_created", "permission_granted", "permit_minted", "execution_admitted", "memory_history_mutated", "deletion_performed", "tool_removed", "agent_spawned", "oea_ter_called"):
            if payload.get(key) is not False:
                raise BrsValidationError("brs.validation.negative_proof", f"{key} must be false")


def brs_record_from_fixture(data: dict[str, Any]) -> RateSupervisorRecord:
    return RateSupervisorRecord(
        record_id=str(data.get("record_id", "brs:fixture")),
        summary=str(data.get("summary", "")),
        observed_at=str(data.get("observed_at", FIXTURE_CLOCK)),
        classification=str(data.get("classification", "unknown")),
        authority_created=bool(data.get("authority_created", False)),
        permission_granted=bool(data.get("permission_granted", False)),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "RateSupervisorRecord",
    "RateSupervisorReceipt",
    "RatePressureSignal",
    "classify_brs_claim_risk",
    "brs_record_from_fixture",
]
