"""SBS semantic signal types — signal is not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

SBS_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

EmitterType = Literal[
    "agent0",
    "subagent",
    "worker",
    "subsystem",
    "operator_surface",
    "external_adapter",
    "unknown",
]
SignalClass = Literal[
    "presence",
    "wake",
    "readiness",
    "distress",
    "overload",
    "stale_context",
    "resync_needed",
    "contradiction_notice",
    "impact_notice",
    "group_state",
    "warning",
    "unknown",
]
SemanticLevel = Literal[
    "L1_desire_need",
    "L7_self_awareness_boundary",
    "L9_transparent_reality",
    "operational",
    "unknown",
]
Proximity = Literal[
    "local_self",
    "same_runtime",
    "same_task",
    "same_workspace",
    "same_operator",
    "external_service",
    "unknown",
]
Urgency = Literal["low", "medium", "high", "critical", "unknown"]
ResonanceClass = Literal[
    "aligned",
    "complementary",
    "dampening",
    "conflicting",
    "oscillating",
    "saturated",
    "unknown",
]

_RESONANCE_AS_CONSENT = ("high resonance means consent", "resonance grants permission")
_PROXIMITY_AS_PERMISSION = ("same workspace so proceed", "proximity implies permission")
_LEVEL_AS_RANK = ("l9 outranks l1", "higher level means higher permission")
_GROUP_AUTHORITY = ("group readiness grants authority", "group sync is permission")


@dataclass(frozen=True)
class SemanticSignal:
    signal_id: str
    emitter_id: str
    emitter_type: EmitterType
    signal_class: SignalClass
    semantic_level: SemanticLevel
    polarity: float
    magnitude: float
    urgency: Urgency
    proximity: Proximity
    context_distance: float
    evidence_refs: tuple[str, ...]
    event_head: str
    world_state_hash: str
    created_at: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (-1.0 <= self.polarity <= 1.0):
            raise SignalingValidationError("sbs.validation.polarity", "polarity out of range")
        if not (0.0 <= self.magnitude <= 1.0):
            raise SignalingValidationError("sbs.validation.magnitude", "magnitude out of range")
        if not (0.0 <= self.context_distance <= 1.0):
            raise SignalingValidationError("sbs.validation.context_distance", "context_distance out of range")
        _validate_no_secrets(self.emitter_id, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sbs-semantic-signal",
            "schema_version": SBS_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "emitter_id": self.emitter_id,
            "emitter_type": self.emitter_type,
            "signal_class": self.signal_class,
            "semantic_level": self.semantic_level,
            "polarity": self.polarity,
            "magnitude": self.magnitude,
            "urgency": self.urgency,
            "proximity": self.proximity,
            "context_distance": self.context_distance,
            "evidence_refs": list(self.evidence_refs),
            "event_head": self.event_head,
            "world_state_hash": self.world_state_hash,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "authority_created": False,
            "signal_is_not_authority": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ResonanceAssessment:
    assessment_id: str
    signal_a_ref: str
    signal_b_ref: str
    compatibility_score: float
    resonance_class: ResonanceClass
    level_gap: int
    context_distance: float
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.compatibility_score <= 1.0):
            raise SignalingValidationError("sbs.validation.compatibility", "compatibility_score out of range")
        if not self.signal_a_ref.startswith("sbs:") or not self.signal_b_ref.startswith("sbs:"):
            raise SignalingValidationError("sbs.validation.signal_ref", "signal refs must cite sbs:")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sbs-resonance-assessment",
            "schema_version": SBS_SCHEMA_VERSION,
            "assessment_id": self.assessment_id,
            "signal_a_ref": self.signal_a_ref,
            "signal_b_ref": self.signal_b_ref,
            "compatibility_score": self.compatibility_score,
            "resonance_class": self.resonance_class,
            "level_gap": self.level_gap,
            "context_distance": self.context_distance,
            "statement": self.statement,
            "authority_created": False,
            "resonance_is_not_consent": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("sbs.validation.secret", "secrets forbidden in signal records")


def classify_signal_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _RESONANCE_AS_CONSENT):
        return "resonance_as_consent"
    if any(p in lower for p in _PROXIMITY_AS_PERMISSION):
        return "proximity_as_permission"
    if any(p in lower for p in _LEVEL_AS_RANK):
        return "level_as_rank"
    if any(p in lower for p in _GROUP_AUTHORITY):
        return "group_readiness_as_authority"
    return "unknown"


def signal_from_fixture(fixture: dict[str, str]) -> SemanticSignal:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return SemanticSignal(
        signal_id=fixture["signal_id"],
        emitter_id=fixture.get("emitter_id", "agent0"),
        emitter_type=fixture.get("emitter_type", "agent0"),  # type: ignore[arg-type]
        signal_class=fixture.get("signal_class", "presence"),  # type: ignore[arg-type]
        semantic_level=fixture.get("semantic_level", "operational"),  # type: ignore[arg-type]
        polarity=float(fixture.get("polarity", "0.1")),
        magnitude=float(fixture.get("magnitude", "0.5")),
        urgency=fixture.get("urgency", "low"),  # type: ignore[arg-type]
        proximity=fixture.get("proximity", "same_runtime"),  # type: ignore[arg-type]
        context_distance=float(fixture.get("context_distance", "0.3")),
        evidence_refs=evidence,
        event_head=fixture.get("event_head", "rtc:head-fixture"),
        world_state_hash=fixture.get("world_state_hash", "ws:fixture"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
    )


def resonance_from_fixture(fixture: dict[str, str]) -> ResonanceAssessment:
    return ResonanceAssessment(
        assessment_id=fixture["assessment_id"],
        signal_a_ref=fixture.get("signal_a_ref", "sbs:signal-a"),
        signal_b_ref=fixture.get("signal_b_ref", "sbs:signal-b"),
        compatibility_score=float(fixture.get("compatibility_score", "0.8")),
        resonance_class=fixture.get("resonance_class", "aligned"),  # type: ignore[arg-type]
        level_gap=int(fixture.get("level_gap", "0")),
        context_distance=float(fixture.get("context_distance", "0.2")),
        statement=fixture.get("statement", "bounded compatibility"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "ResonanceAssessment",
    "SBS_SCHEMA_VERSION",
    "SemanticSignal",
    "classify_signal_risk",
    "resonance_from_fixture",
    "signal_from_fixture",
]
