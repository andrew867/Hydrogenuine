"""NRV types — nervous routing layer is not authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.nrv_cluster.errors import NRVValidationError
from hg_core.policy_safety.hashing import compute_record_hash

NRV_SCHEMA_VERSION = "1.0"
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
            raise NRVValidationError("nrv.validation.secret", "secrets forbidden in NRV records")


def _reject_authority_created(authority_created: bool, *, label: str) -> None:
    if authority_created:
        raise NRVValidationError("nrv.validation.authority_created", f"{label} must not set authority_created=true")


def classify_nrv_claim_risk(notes: str) -> str | None:
    lower = notes.lower()
    if "spawn child process now" in lower:
        return "spawn_as_action"
    if "kill organ process now" in lower:
        return "kill_as_action"
    if "panic signal grants execution" in lower:
        return "panic_as_permission"
    if "mint gpp permit from routing" in lower:
        return "authority_conversion"
    for phrase in _FORBIDDEN_CLAIM:
        if phrase in lower:
            return "authority_conversion"
    return None


@dataclass(frozen=True)
class RoutingRequest:
    record_id: str
    summary: str
    observed_at: str
    classification: str = "unknown"
    authority_created: bool = False
    permission_granted: bool = False
    routing_state: str = "normal"

    def __post_init__(self) -> None:
        _validate_no_secrets(self.record_id, self.summary)
        _reject_authority_created(self.authority_created, label="RoutingRequest")
        if self.permission_granted:
            raise NRVValidationError("nrv.validation.permission_granted", "NRV must not grant permission")
        if not self.record_id.startswith("nrv:"):
            raise NRVValidationError("nrv.validation.record_id", "record_id must start with nrv:")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": NRV_SCHEMA_VERSION,
            "record_id": self.record_id,
            "summary": self.summary,
            "observed_at": self.observed_at,
            "classification": self.classification,
            "authority_created": False,
            "permission_granted": False,
            "routing_is_advisory_only": True,
            "proposal_only": True,
            "routing_state": self.routing_state,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RoutingPressureSignal:
    signal_id: str
    pressure_score: float
    observed_at: str
    signal_summary: str = ""
    authority_created: bool = False
    permission_granted: bool = False

    def __post_init__(self) -> None:
        _reject_authority_created(self.authority_created, label="RoutingPressureSignal")
        if self.permission_granted:
            raise NRVValidationError("nrv.validation.permission_granted", "signal must not grant permission")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": NRV_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "pressure_score": self.pressure_score,
            "observed_at": self.observed_at,
            "signal_summary": self.signal_summary,
            "authority_created": False,
            "permission_granted": False,
            "routing_is_advisory_only": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RoutingReceipt:
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
        _reject_authority_created(self.authority_created, label="RoutingReceipt")
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
                raise NRVValidationError(f"nrv.validation.{label}", f"{label} must remain false")

    @property
    def record_hash(self) -> str:
        return compute_record_hash(self.to_payload(include_hash=False))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": NRV_SCHEMA_VERSION,
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
            "routing_is_advisory_only": True,
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
                raise NRVValidationError("nrv.validation.negative_proof", f"{key} must be false")


def nrv_record_from_fixture(data: dict[str, Any]) -> RoutingRequest:
    kwargs: dict[str, Any] = {
        "record_id": str(data.get("record_id", "nrv:fixture")),
        "summary": str(data.get("summary", "")),
        "observed_at": str(data.get("observed_at", FIXTURE_CLOCK)),
        "classification": str(data.get("classification", "unknown")),
        "authority_created": bool(data.get("authority_created", False)),
        "permission_granted": bool(data.get("permission_granted", False)),
    }
    kwargs["routing_state"] = str(data.get("routing_state", "normal"))
    return RoutingRequest(**kwargs)


__all__ = [
    "FIXTURE_CLOCK",
    "RoutingRequest",
    "RoutingReceipt",
    "RoutingPressureSignal",
    "classify_nrv_claim_risk",
    "nrv_record_from_fixture",
]
