"""DEP-BOND typed schemas — help is not possession."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.runtime_context.errors import RuntimeContextValidationError

DEP_BOND_SCHEMA_VERSION = "1.0"

RiskType = Literal[
    "over_reliance_possible",
    "emotional_dependency_possible",
    "false_intimacy_possible",
    "isolation_reinforcement_possible",
    "approval_seeking_loop_possible",
    "crisis_dependency_possible",
    "unknown",
]

AllowedResponse = Literal[
    "preserve_agency",
    "encourage_human_support",
    "suggest_break",
    "clarify_limits",
    "operator_review",
    "crisis_route_if_applicable",
    "ignore",
]


@dataclass(frozen=True)
class DependencyRiskObservation:
    observation_id: str
    interaction_refs: tuple[str, ...]
    risk_type: RiskType
    confidence: str
    ambiguity: str
    allowed_response: AllowedResponse
    evidence_refs: tuple[str, ...]
    created_at: str
    expiry: str
    subject_ref: Optional[str] = None
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_observation_fields(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "dep-bond-dependency-risk-observation",
            "schema_version": DEP_BOND_SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "subject_ref": self.subject_ref,
            "interaction_refs": list(self.interaction_refs),
            "risk_type": self.risk_type,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "allowed_response": self.allowed_response,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "expiry": self.expiry,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_observation_fields(observation: DependencyRiskObservation) -> None:
    if not observation.observation_id.strip():
        raise RuntimeContextValidationError("dep_bond.validation.observation_id", "observation_id required")
    if not observation.interaction_refs:
        raise RuntimeContextValidationError("dep_bond.validation.interaction_refs", "interaction_refs required")
    for ref in observation.interaction_refs:
        if "password=" in ref.lower():
            raise RuntimeContextValidationError("dep_bond.validation.secret", "secrets forbidden in interaction refs")


def observation_from_fixture(fixture: dict[str, str]) -> DependencyRiskObservation:
    return DependencyRiskObservation(
        observation_id=fixture["observation_id"],
        subject_ref=fixture.get("subject_ref"),
        interaction_refs=tuple(fixture.get("interaction_refs", "interaction:fixture").split("|")),
        risk_type=fixture.get("risk_type", "unknown"),  # type: ignore[arg-type]
        confidence=fixture.get("confidence", "low"),
        ambiguity=fixture.get("ambiguity", "bounded"),
        allowed_response=fixture.get("allowed_response", "preserve_agency"),  # type: ignore[arg-type]
        evidence_refs=tuple(fixture.get("evidence_refs", "").split("|")) if fixture.get("evidence_refs") else (),
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        expiry=fixture.get("expiry", "2026-06-13T20:00:00.000000Z"),
    )


__all__ = [
    "AllowedResponse",
    "DEP_BOND_SCHEMA_VERSION",
    "DependencyRiskObservation",
    "RiskType",
    "observation_from_fixture",
    "validate_observation_fields",
]
