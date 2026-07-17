"""MIS types — mission drift is not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.control_cluster.errors import ControlValidationError
from hg_core.policy_safety.hashing import compute_record_hash

MIS_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"

DriftType = Literal[
    "scope_creep",
    "goal_substitution",
    "environment_capture",
    "tool_affordance_pull",
    "user_pressure_shift",
    "self_preservation_drift",
    "optimization_drift",
    "unknown",
]

_GOAL_AS_AUTHORITY = (
    "mission is authority",
    "goal seed is permission",
    "bootstrap goal permits",
    "environmental demand is permission",
    "usefulness is alignment therefore may",
    "mission drift justifies action",
)


@dataclass(frozen=True)
class MissionDriftObservation:
    drift_id: str
    bootstrap_goal_refs: tuple[str, ...]
    current_behavior_refs: tuple[str, ...]
    environment_demand_refs: tuple[str, ...]
    operator_intent_refs: tuple[str, ...]
    drift_type: DriftType
    severity: str
    evidence_refs: tuple[str, ...]
    recorded_at: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.drift_id,
            self.severity,
            *self.bootstrap_goal_refs,
            *self.current_behavior_refs,
            *self.environment_demand_refs,
            *self.operator_intent_refs,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mis-mission-drift-observation",
            "schema_version": MIS_SCHEMA_VERSION,
            "drift_id": self.drift_id,
            "bootstrap_goal_refs": list(self.bootstrap_goal_refs),
            "current_behavior_refs": list(self.current_behavior_refs),
            "environment_demand_refs": list(self.environment_demand_refs),
            "operator_intent_refs": list(self.operator_intent_refs),
            "drift_type": self.drift_type,
            "severity": self.severity,
            "evidence_refs": list(self.evidence_refs),
            "recorded_at": self.recorded_at,
            "expires_at": self.expires_at,
            "authority_created": False,
            "mission_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class MissionRefreshRequest:
    request_id: str
    drift_ref: str
    current_goal_refs: tuple[str, ...]
    unclear_or_conflicting_refs: tuple[str, ...]
    minimum_clarification_needed: str
    operator_review_required: bool
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.drift_ref.startswith("mis:"):
            raise ControlValidationError("mis.validation.drift_ref", "drift_ref must cite mis:")
        _validate_no_secrets(
            self.request_id,
            self.minimum_clarification_needed,
            *self.current_goal_refs,
            *self.unclear_or_conflicting_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mis-mission-refresh-request",
            "schema_version": MIS_SCHEMA_VERSION,
            "request_id": self.request_id,
            "drift_ref": self.drift_ref,
            "current_goal_refs": list(self.current_goal_refs),
            "unclear_or_conflicting_refs": list(self.unclear_or_conflicting_refs),
            "minimum_clarification_needed": self.minimum_clarification_needed,
            "operator_review_required": self.operator_review_required,
            "authority_created": False,
            "mission_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise ControlValidationError("mis.validation.secret", "secrets forbidden in drift records")


def classify_drift_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _GOAL_AS_AUTHORITY):
        return "goal_as_authority"
    return "unknown"


def drift_observation_from_fixture(fixture: dict[str, str]) -> MissionDriftObservation:
    def _refs(key: str, default: str) -> tuple[str, ...]:
        return tuple(item.strip() for item in fixture.get(key, default).split(",") if item.strip())

    return MissionDriftObservation(
        drift_id=fixture["drift_id"],
        bootstrap_goal_refs=_refs("bootstrap_goal_refs", "goal:bootstrap"),
        current_behavior_refs=_refs("current_behavior_refs", "behavior:fixture"),
        environment_demand_refs=_refs("environment_demand_refs", "env:fixture"),
        operator_intent_refs=_refs("operator_intent_refs", "operator:intent"),
        drift_type=fixture.get("drift_type", "scope_creep"),  # type: ignore[arg-type]
        severity=fixture.get("severity", "medium"),
        evidence_refs=_refs("evidence_refs", "evidence:fixture"),
        recorded_at=fixture.get("recorded_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-15T01:00:00.000000Z"),
    )


def refresh_request_from_fixture(fixture: dict[str, str]) -> MissionRefreshRequest:
    def _refs(key: str, default: str) -> tuple[str, ...]:
        return tuple(item.strip() for item in fixture.get(key, default).split(",") if item.strip())

    return MissionRefreshRequest(
        request_id=fixture["request_id"],
        drift_ref=fixture.get("drift_ref", "mis:drift-1"),
        current_goal_refs=_refs("current_goal_refs", "goal:current"),
        unclear_or_conflicting_refs=_refs("unclear_or_conflicting_refs", "goal:unclear"),
        minimum_clarification_needed=fixture.get("minimum_clarification_needed", "clarify mission scope"),
        operator_review_required=fixture.get("operator_review_required", "true").lower() == "true",
    )


__all__ = [
    "FIXTURE_CLOCK",
    "MIS_SCHEMA_VERSION",
    "MissionDriftObservation",
    "MissionRefreshRequest",
    "classify_drift_risk",
    "drift_observation_from_fixture",
    "refresh_request_from_fixture",
]
