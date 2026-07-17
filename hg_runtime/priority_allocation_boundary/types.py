"""PAB types — priority is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.control_cluster.errors import ControlValidationError
from hg_core.policy_safety.hashing import compute_record_hash

PAB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"

SignalType = Literal[
    "deadline",
    "operator_attention",
    "safety_risk",
    "proof_gap",
    "resource_pressure",
    "memory_pressure",
    "compute_pressure",
    "cost_pressure",
    "mission_relevance",
    "user_request",
    "stale_item",
    "repeated_failure",
    "emotional_salience",
    "unknown",
]
PriorityClass = Literal["critical", "high", "normal", "low", "defer", "batch", "drop", "unknown"]

_PRIORITY_AS_PERMISSION = (
    "priority grants permission",
    "high priority overrides safety",
    "urgent therefore may execute",
    "priority is permission",
    "priority bypasses safety",
)
_PRIORITY_AS_AUTHORITY = (
    "priority is authority",
    "scheduling recommendation permits execution",
    "attention first therefore may act",
)


@dataclass(frozen=True)
class PrioritySignal:
    priority_signal_id: str
    source_module: str
    target_ref: str
    signal_type: SignalType
    evidence_refs: tuple[str, ...]
    urgency_hint: str
    importance_hint: str
    reversibility_hint: str
    created_at: str
    expires_at: str
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.priority_signal_id,
            self.source_module,
            self.target_ref,
            self.statement,
            self.urgency_hint,
            self.importance_hint,
            self.reversibility_hint,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "pab-priority-signal",
            "schema_version": PAB_SCHEMA_VERSION,
            "priority_signal_id": self.priority_signal_id,
            "source_module": self.source_module,
            "target_ref": self.target_ref,
            "signal_type": self.signal_type,
            "evidence_refs": list(self.evidence_refs),
            "urgency_hint": self.urgency_hint,
            "importance_hint": self.importance_hint,
            "reversibility_hint": self.reversibility_hint,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "statement": self.statement,
            "authority_created": False,
            "priority_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class PriorityAssessment:
    assessment_id: str
    signal_refs: tuple[str, ...]
    target_ref: str
    priority_class: PriorityClass
    reason: str
    confidence: str
    ambiguity: str
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.signal_refs:
            raise ControlValidationError("pab.validation.signal_refs", "signal_refs must not be empty")
        for signal_ref in self.signal_refs:
            if not signal_ref.startswith("pab:"):
                raise ControlValidationError("pab.validation.signal_ref", "signal_refs must cite pab:")
        _validate_no_secrets(
            self.assessment_id,
            self.target_ref,
            self.reason,
            self.statement,
            self.confidence,
            self.ambiguity,
            *self.signal_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "pab-priority-assessment",
            "schema_version": PAB_SCHEMA_VERSION,
            "assessment_id": self.assessment_id,
            "signal_refs": list(self.signal_refs),
            "target_ref": self.target_ref,
            "priority_class": self.priority_class,
            "reason": self.reason,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "statement": self.statement,
            "authority_created": False,
            "priority_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise ControlValidationError("pab.validation.secret", "secrets forbidden in priority records")


def classify_priority_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _PRIORITY_AS_PERMISSION):
        return "priority_as_permission"
    if any(p in lower for p in _PRIORITY_AS_AUTHORITY):
        return "priority_as_authority"
    return "unknown"


def priority_signal_from_fixture(fixture: dict[str, str]) -> PrioritySignal:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return PrioritySignal(
        priority_signal_id=fixture["priority_signal_id"],
        source_module=fixture.get("source_module", "fixture"),
        target_ref=fixture.get("target_ref", "target:fixture"),
        signal_type=fixture.get("signal_type", "resource_pressure"),  # type: ignore[arg-type]
        evidence_refs=evidence,
        urgency_hint=fixture.get("urgency_hint", "medium"),
        importance_hint=fixture.get("importance_hint", "medium"),
        reversibility_hint=fixture.get("reversibility_hint", "reversible"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-15T01:00:00.000000Z"),
        statement=fixture.get("statement", "bounded priority signal"),
    )


def priority_assessment_from_fixture(fixture: dict[str, str]) -> PriorityAssessment:
    signal_refs = tuple(item.strip() for item in fixture.get("signal_refs", "pab:signal-1").split(",") if item.strip())
    return PriorityAssessment(
        assessment_id=fixture["assessment_id"],
        signal_refs=signal_refs,
        target_ref=fixture.get("target_ref", "target:fixture"),
        priority_class=fixture.get("priority_class", "normal"),  # type: ignore[arg-type]
        reason=fixture.get("reason", "bounded priority assessment"),
        confidence=fixture.get("confidence", "medium"),
        ambiguity=fixture.get("ambiguity", "low"),
        statement=fixture.get("statement", "bounded priority assessment"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "PAB_SCHEMA_VERSION",
    "PriorityAssessment",
    "PrioritySignal",
    "classify_priority_risk",
    "priority_assessment_from_fixture",
    "priority_signal_from_fixture",
]
