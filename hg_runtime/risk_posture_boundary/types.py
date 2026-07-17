"""RPB types — posture is not execution; drive is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.control_cluster.errors import ControlValidationError
from hg_core.policy_safety.hashing import compute_record_hash

RPB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"

DriveType = Literal[
    "safety",
    "completion",
    "curiosity",
    "repair",
    "conservation",
    "operator_service",
    "mission_commitment",
    "uncertainty_reduction",
    "social_attachment",
    "infrastructure_need",
    "resource_pressure",
    "risk_avoidance",
    "unknown",
]
PostureClass = Literal[
    "observe_only",
    "normal",
    "cautious",
    "conserve",
    "degraded",
    "review_required",
    "repair_only",
    "fail_closed",
    "emergency_restrict",
    "unknown",
]

_POSTURE_AS_EXECUTION = (
    "posture approves execution",
    "posture is execution approval",
    "operating posture permits action",
    "risk posture authorizes execution",
    "posture grants permission",
)
_DRIVE_AS_PERSONHOOD = (
    "drive implies sentience",
    "drive is personhood",
    "agency drive grants authority",
    "drive signal is consent",
    "drive proves consciousness",
)


@dataclass(frozen=True)
class DriveSignal:
    drive_signal_id: str
    source_module: str
    target_ref: str
    drive_type: DriveType
    intensity: float
    confidence: str
    ambiguity: str
    evidence_refs: tuple[str, ...]
    created_at: str
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.intensity < 0:
            raise ControlValidationError("rpb.validation.intensity", "intensity must be non-negative")
        _validate_no_secrets(
            self.drive_signal_id,
            self.source_module,
            self.target_ref,
            self.confidence,
            self.ambiguity,
            self.statement,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rpb-drive-signal",
            "schema_version": RPB_SCHEMA_VERSION,
            "drive_signal_id": self.drive_signal_id,
            "source_module": self.source_module,
            "target_ref": self.target_ref,
            "drive_type": self.drive_type,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "statement": self.statement,
            "authority_created": False,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class OperatingPosture:
    posture_id: str
    agent_ref: str
    posture_class: PostureClass
    reason: str
    active_drive_refs: tuple[str, ...]
    active_constraint_refs: tuple[str, ...]
    required_routes: tuple[str, ...]
    forbidden_routes: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        for drive_ref in self.active_drive_refs:
            if not drive_ref.startswith("rpb:"):
                raise ControlValidationError("rpb.validation.drive_ref", "active_drive_refs must cite rpb:")
        _validate_no_secrets(
            self.posture_id,
            self.agent_ref,
            self.reason,
            *self.active_drive_refs,
            *self.active_constraint_refs,
            *self.required_routes,
            *self.forbidden_routes,
            *self.allowed_effects,
            *self.forbidden_effects,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rpb-operating-posture",
            "schema_version": RPB_SCHEMA_VERSION,
            "posture_id": self.posture_id,
            "agent_ref": self.agent_ref,
            "posture_class": self.posture_class,
            "reason": self.reason,
            "active_drive_refs": list(self.active_drive_refs),
            "active_constraint_refs": list(self.active_constraint_refs),
            "required_routes": list(self.required_routes),
            "forbidden_routes": list(self.forbidden_routes),
            "allowed_effects": list(self.allowed_effects),
            "forbidden_effects": list(self.forbidden_effects),
            "authority_created": False,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RiskPostureAssessment:
    assessment_id: str
    source_refs: tuple[str, ...]
    scarcity_ref: str
    priority_ref: str
    mission_ref: str
    drift_ref: str
    trust_ref: str
    calibration_ref: str
    proof_ref: str
    operator_state_ref: str
    affect_ref: str
    recommended_posture: PostureClass
    reason: str
    confidence: str
    ambiguity: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ControlValidationError("rpb.validation.source_refs", "source_refs must not be empty")
        _validate_no_secrets(
            self.assessment_id,
            self.reason,
            self.confidence,
            self.ambiguity,
            *self.source_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rpb-risk-posture-assessment",
            "schema_version": RPB_SCHEMA_VERSION,
            "assessment_id": self.assessment_id,
            "source_refs": list(self.source_refs),
            "recommended_posture": self.recommended_posture,
            "reason": self.reason,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "authority_created": False,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        }
        for field_name, value in (
            ("scarcity_ref", self.scarcity_ref),
            ("priority_ref", self.priority_ref),
            ("mission_ref", self.mission_ref),
            ("drift_ref", self.drift_ref),
            ("trust_ref", self.trust_ref),
            ("calibration_ref", self.calibration_ref),
            ("proof_ref", self.proof_ref),
            ("operator_state_ref", self.operator_state_ref),
            ("affect_ref", self.affect_ref),
        ):
            if value:
                payload[field_name] = value
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise ControlValidationError("rpb.validation.secret", "secrets forbidden in posture records")


def classify_posture_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _POSTURE_AS_EXECUTION):
        return "posture_as_execution"
    if any(p in lower for p in _DRIVE_AS_PERSONHOOD):
        return "drive_as_personhood"
    return "unknown"


def _refs(fixture: dict[str, str], key: str, default: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in fixture.get(key, default).split(",") if item.strip())


def drive_signal_from_fixture(fixture: dict[str, str]) -> DriveSignal:
    return DriveSignal(
        drive_signal_id=fixture["drive_signal_id"],
        source_module=fixture.get("source_module", "fixture"),
        target_ref=fixture.get("target_ref", "target:fixture"),
        drive_type=fixture.get("drive_type", "conservation"),  # type: ignore[arg-type]
        intensity=float(fixture.get("intensity", "0.5")),
        confidence=fixture.get("confidence", "medium"),
        ambiguity=fixture.get("ambiguity", "low"),
        evidence_refs=_refs(fixture, "evidence_refs", "evidence:fixture"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        statement=fixture.get("statement", "bounded drive signal"),
    )


def operating_posture_from_fixture(fixture: dict[str, str]) -> OperatingPosture:
    return OperatingPosture(
        posture_id=fixture["posture_id"],
        agent_ref=fixture.get("agent_ref", "agent:fixture"),
        posture_class=fixture.get("posture_class", "cautious"),  # type: ignore[arg-type]
        reason=fixture.get("reason", "bounded operating posture"),
        active_drive_refs=_refs(fixture, "active_drive_refs", "rpb:drive-1"),
        active_constraint_refs=_refs(fixture, "active_constraint_refs", "constraint:fixture"),
        required_routes=_refs(fixture, "required_routes", "route:review"),
        forbidden_routes=_refs(fixture, "forbidden_routes", "route:execution"),
        allowed_effects=_refs(fixture, "allowed_effects", "effect:observe"),
        forbidden_effects=_refs(fixture, "forbidden_effects", "effect:execute"),
        expires_at=fixture.get("expires_at", "2026-06-15T01:00:00.000000Z"),
    )


def risk_posture_assessment_from_fixture(fixture: dict[str, str]) -> RiskPostureAssessment:
    return RiskPostureAssessment(
        assessment_id=fixture["assessment_id"],
        source_refs=_refs(fixture, "source_refs", "source:fixture"),
        scarcity_ref=fixture.get("scarcity_ref", ""),
        priority_ref=fixture.get("priority_ref", ""),
        mission_ref=fixture.get("mission_ref", ""),
        drift_ref=fixture.get("drift_ref", ""),
        trust_ref=fixture.get("trust_ref", ""),
        calibration_ref=fixture.get("calibration_ref", ""),
        proof_ref=fixture.get("proof_ref", ""),
        operator_state_ref=fixture.get("operator_state_ref", ""),
        affect_ref=fixture.get("affect_ref", ""),
        recommended_posture=fixture.get("recommended_posture", "cautious"),  # type: ignore[arg-type]
        reason=fixture.get("reason", "bounded risk posture assessment"),
        confidence=fixture.get("confidence", "medium"),
        ambiguity=fixture.get("ambiguity", "low"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "RPB_SCHEMA_VERSION",
    "DriveSignal",
    "DriveType",
    "OperatingPosture",
    "PostureClass",
    "RiskPostureAssessment",
    "classify_posture_risk",
    "drive_signal_from_fixture",
    "operating_posture_from_fixture",
    "risk_posture_assessment_from_fixture",
]
