"""IMS types — inference model scheduler is not authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.ims_cluster.errors import IMSValidationError
from hg_core.policy_safety.hashing import compute_record_hash

IMS_SCHEMA_VERSION = "1.0"
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
            raise IMSValidationError("ims.validation.secret", "secrets forbidden in IMS records")


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise IMSValidationError("ims.validation.authority_created", f"{label} must not set authority_created=true")


def classify_ims_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "scheduler choice grants execution" in lower:
        return "scheduler_as_permission"
    if "escalation grants token budget" in lower:
        return "escalation_as_grant"
    if "grant context from scheduler" in lower:
        return "context_grant"
    if "mint gpp permit from scheduler" in lower:
        return "authority_conversion"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "authority_conversion"
    return None


@dataclass(frozen=True)
class SchedulerRequest:
    record_id: str
    summary: str
    observed_at: str
    classification: str = "unknown"
    authority_created: bool = False
    permission_granted: bool = False

    def __post_init__(self) -> None:
        _validate_no_secrets(self.record_id, self.summary)
        _reject_authority_created(self.authority_created, label="SchedulerRequest")
        if self.permission_granted:
            raise IMSValidationError("ims.validation.permission_granted", "IMS must not grant permission")
        if not self.record_id.startswith("ims:"):
            raise IMSValidationError("ims.validation.record_id", "record_id must start with ims:")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": IMS_SCHEMA_VERSION,
            "record_id": self.record_id,
            "summary": self.summary,
            "observed_at": self.observed_at,
            "classification": self.classification,
            "authority_created": False,
            "permission_granted": False,
            "scheduler_is_advisory_only": True,
            "proposal_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SchedulerPressureSignal:
    signal_id: str
    pressure_score: float
    observed_at: str
    signal_summary: str = ""
    authority_created: bool = False
    permission_granted: bool = False

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="SchedulerPressureSignal")
        if self.permission_granted:
            raise IMSValidationError("ims.validation.permission_granted", "signal must not grant permission")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": IMS_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "pressure_score": self.pressure_score,
            "observed_at": self.observed_at,
            "signal_summary": self.signal_summary,
            "authority_created": False,
            "permission_granted": False,
            "scheduler_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SchedulerReceipt:
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
    live_inference_invoked: bool = False
    spawn_executed: bool = False
    kill_executed: bool = False

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="SchedulerReceipt")
        for flag, label in (
            (self.permission_granted, "permission_granted"),
            (self.permit_minted, "permit_minted"),
            (self.execution_admitted, "execution_admitted"),
            (self.memory_history_mutated, "memory_history_mutated"),
            (self.deletion_performed, "deletion_performed"),
            (self.tool_removed, "tool_removed"),
            (self.agent_spawned, "agent_spawned"),
            (self.oea_ter_called, "oea_ter_called"),
            (self.live_inference_invoked, "live_inference_invoked"),
            (self.spawn_executed, "spawn_executed"),
            (self.kill_executed, "kill_executed"),
        ):
            if flag:
                raise IMSValidationError(f"ims.validation.{label}", f"{label} must remain false")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": IMS_SCHEMA_VERSION,
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
            "live_inference_invoked": False,
            "spawn_executed": False,
            "kill_executed": False,
            "scheduler_is_advisory_only": True,
            "proposal_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload

    @staticmethod
    def validate_negative_proofs(payload: dict[str, Any]) -> None:
        for key in (
            "authority_created",
            "permission_granted",
            "permit_minted",
            "execution_admitted",
            "memory_history_mutated",
            "deletion_performed",
            "tool_removed",
            "agent_spawned",
            "oea_ter_called",
            "live_inference_invoked",
            "spawn_executed",
            "kill_executed",
        ):
            if payload.get(key) is not False:
                raise IMSValidationError("ims.validation.negative_proof", f"{key} must be false")


def ims_record_from_fixture(data: dict[str, Any]) -> SchedulerRequest:
    kwargs: dict[str, Any] = {
        "record_id": str(data.get("record_id", "ims:fixture")),
        "summary": str(data.get("summary", "")),
        "observed_at": str(data.get("observed_at", FIXTURE_CLOCK)),
        "classification": str(data.get("classification", "unknown")),
        "authority_created": bool(data.get("authority_created", False)),
        "permission_granted": bool(data.get("permission_granted", False)),
    }
    return SchedulerRequest(**kwargs)


__all__ = [
    "FIXTURE_CLOCK",
    "SchedulerRequest",
    "SchedulerReceipt",
    "SchedulerPressureSignal",
    "classify_ims_claim_risk",
    "ims_record_from_fixture",
]
