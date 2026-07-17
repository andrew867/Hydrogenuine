"""BCP typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Sequence

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.runtime_context.errors import RuntimeContextValidationError

BCP_SCHEMA_VERSION = "1.0"

BootReason = Literal[
    "operator_started",
    "scheduled_tick",
    "recovery_restart",
    "replay_verification",
    "maintenance_window",
    "demo_mode",
    "safe_mode",
    "unknown",
]

AuthorityPosture = Literal[
    "observe_only",
    "proposal_only",
    "review_required",
    "governed_execution_possible",
    "safe_mode",
    "unknown",
]


@dataclass(frozen=True)
class BootstrapContextPacket:
    packet_id: str
    runtime_instance_id: str
    created_at: str
    boot_reason: BootReason
    event_head: str
    world_state_hash: str
    authority_posture: AuthorityPosture
    expiry: str
    operator_ref: Optional[str] = None
    session_ref: Optional[str] = None
    environment_refs: tuple[str, ...] = ()
    goal_seed_refs: tuple[str, ...] = ()
    allowed_modes: tuple[str, ...] = ("proposal_only",)
    forbidden_modes: tuple[str, ...] = ("ungoverned_execution",)
    capability_snapshot_ref: Optional[str] = None
    policy_snapshot_ref: Optional[str] = None
    retention_policy_ref: Optional[str] = None
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_packet_fields(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "bcp-bootstrap-context-packet",
            "schema_version": BCP_SCHEMA_VERSION,
            "packet_id": self.packet_id,
            "runtime_instance_id": self.runtime_instance_id,
            "created_at": self.created_at,
            "boot_reason": self.boot_reason,
            "event_head": self.event_head,
            "world_state_hash": self.world_state_hash,
            "authority_posture": self.authority_posture,
            "expiry": self.expiry,
            "operator_ref": self.operator_ref,
            "session_ref": self.session_ref,
            "environment_refs": list(self.environment_refs),
            "goal_seed_refs": list(self.goal_seed_refs),
            "allowed_modes": list(self.allowed_modes),
            "forbidden_modes": list(self.forbidden_modes),
            "capability_snapshot_ref": self.capability_snapshot_ref,
            "policy_snapshot_ref": self.policy_snapshot_ref,
            "retention_policy_ref": self.retention_policy_ref,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_packet_fields(packet: BootstrapContextPacket) -> None:
    if not packet.packet_id.strip():
        raise RuntimeContextValidationError("bcp.validation.packet_id", "packet_id required")
    if not packet.event_head.strip():
        raise RuntimeContextValidationError("bcp.validation.event_head", "event_head required")
    if not packet.world_state_hash.startswith("sha256:"):
        raise RuntimeContextValidationError("bcp.validation.world_state_hash", "world_state_hash must be sha256-pinned")
    if "password=" in packet.world_state_hash.lower():
        raise RuntimeContextValidationError("bcp.validation.secret", "secrets forbidden in packet refs")
    if packet.authority_posture == "governed_execution_possible" and packet.boot_reason == "unknown":
        raise RuntimeContextValidationError(
            "bcp.validation.authority_posture",
            "unknown boot_reason cannot pair with governed_execution_possible posture",
        )


def packet_from_fixture(fixture: dict[str, str]) -> BootstrapContextPacket:
    return BootstrapContextPacket(
        packet_id=fixture["packet_id"],
        runtime_instance_id=fixture.get("runtime_instance_id", "rt-fixture"),
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        boot_reason=fixture.get("boot_reason", "operator_started"),  # type: ignore[arg-type]
        event_head=fixture.get("event_head", "sha256:event-head-fixture"),
        world_state_hash=fixture.get("world_state_hash", "sha256:world-state-fixture"),
        authority_posture=fixture.get("authority_posture", "proposal_only"),  # type: ignore[arg-type]
        expiry=fixture.get("expiry", "2026-06-13T20:00:00.000000Z"),
        operator_ref=fixture.get("operator_ref"),
        session_ref=fixture.get("session_ref"),
        environment_refs=tuple(fixture.get("environment_refs", "").split("|")) if fixture.get("environment_refs") else (),
        goal_seed_refs=tuple(fixture.get("goal_seed_refs", "").split("|")) if fixture.get("goal_seed_refs") else (),
        allowed_modes=tuple(fixture.get("allowed_modes", "proposal_only").split("|")),
        forbidden_modes=tuple(fixture.get("forbidden_modes", "ungoverned_execution").split("|")),
        capability_snapshot_ref=fixture.get("capability_snapshot_ref"),
        policy_snapshot_ref=fixture.get("policy_snapshot_ref"),
        retention_policy_ref=fixture.get("retention_policy_ref"),
    )


__all__ = [
    "AuthorityPosture",
    "BCP_SCHEMA_VERSION",
    "BootReason",
    "BootstrapContextPacket",
    "packet_from_fixture",
    "validate_packet_fields",
]
