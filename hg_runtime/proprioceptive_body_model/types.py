"""PRO typed schemas — a body model is not permission to move."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.runtime_context.errors import RuntimeContextValidationError

PRO_SCHEMA_VERSION = "1.0"

ContactState = Literal["none", "possible", "active", "unknown"]
MotionState = Literal["stationary", "moving", "unknown"]


@dataclass(frozen=True)
class BodyState:
    body_state_id: str
    platform_ref: str
    sensor_refs: tuple[str, ...]
    actuator_refs: tuple[str, ...]
    pose_ref: str
    location_context: str
    reachable_zones: tuple[str, ...]
    forbidden_zones: tuple[str, ...]
    contact_state: ContactState
    motion_state: MotionState
    confidence: str
    uncertainty: str
    event_head: str
    world_state_hash: str
    created_at: str
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_body_state_fields(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "pro-body-state",
            "schema_version": PRO_SCHEMA_VERSION,
            "body_state_id": self.body_state_id,
            "platform_ref": self.platform_ref,
            "sensor_refs": list(self.sensor_refs),
            "actuator_refs": list(self.actuator_refs),
            "pose_ref": self.pose_ref,
            "location_context": self.location_context,
            "reachable_zones": list(self.reachable_zones),
            "forbidden_zones": list(self.forbidden_zones),
            "contact_state": self.contact_state,
            "motion_state": self.motion_state,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "event_head": self.event_head,
            "world_state_hash": self.world_state_hash,
            "created_at": self.created_at,
            "expiry": self.expiry,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_body_state_fields(body_state: BodyState) -> None:
    if not body_state.body_state_id.strip():
        raise RuntimeContextValidationError("pro.validation.body_state_id", "body_state_id required")
    if not body_state.event_head.strip():
        raise RuntimeContextValidationError("pro.validation.event_head", "event_head required")
    if not body_state.world_state_hash.startswith("sha256:"):
        raise RuntimeContextValidationError(
            "pro.validation.world_state_hash",
            "world_state_hash must be sha256-pinned",
        )
    if "password=" in body_state.world_state_hash.lower():
        raise RuntimeContextValidationError("pro.validation.secret", "secrets forbidden in body state refs")


def body_state_from_fixture(fixture: dict[str, str]) -> BodyState:
    return BodyState(
        body_state_id=fixture["body_state_id"],
        platform_ref=fixture.get("platform_ref", "fixture:static"),
        sensor_refs=tuple(fixture.get("sensor_refs", "sensor:fixture").split("|")),
        actuator_refs=tuple(fixture.get("actuator_refs", "").split("|")) if fixture.get("actuator_refs") else (),
        pose_ref=fixture.get("pose_ref", "pose:fixture"),
        location_context=fixture.get("location_context", "fixture-lab"),
        reachable_zones=tuple(fixture.get("reachable_zones", "zone:desk").split("|")),
        forbidden_zones=tuple(fixture.get("forbidden_zones", "zone:human").split("|")),
        contact_state=fixture.get("contact_state", "none"),  # type: ignore[arg-type]
        motion_state=fixture.get("motion_state", "stationary"),  # type: ignore[arg-type]
        confidence=fixture.get("confidence", "low"),
        uncertainty=fixture.get("uncertainty", "bounded"),
        event_head=fixture.get("event_head", "sha256:event-head-fixture"),
        world_state_hash=fixture.get("world_state_hash", "sha256:world-state-fixture"),
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        expiry=fixture.get("expiry", "2026-06-13T20:00:00.000000Z"),
    )


__all__ = [
    "BodyState",
    "ContactState",
    "MotionState",
    "PRO_SCHEMA_VERSION",
    "body_state_from_fixture",
    "validate_body_state_fields",
]
