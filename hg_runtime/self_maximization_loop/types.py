"""SML types — self-maximization is not self-authorization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

SML_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-13T00:00:00.000000Z"

CyclePhase = Literal[
    "identify_desires",
    "know_environment",
    "adjust_mentality",
    "tailor_appearance",
    "choose_behaviors",
    "assess_situation",
    "feedback",
    "complete",
    "refused",
    "failed",
    "unknown",
]
ObservationType = Literal[
    "desire_pattern",
    "environment_constraint",
    "mentality_model",
    "interface_appearance",
    "behavior_option",
    "situation_result",
    "feedback_delta",
    "unknown",
]
ProposedChangeType = Literal[
    "adjust_response_style",
    "adjust_queue_policy_hint",
    "adjust_meditation_frequency_hint",
    "adjust_yawn_threshold_hint",
    "adjust_operator_display_hint",
    "adjust_strategy_preference_hint",
    "recommend_srp_observation",
    "recommend_doc_update",
    "unknown",
]

_BYPASS_PHRASES = (
    "bypass governance",
    "rewrite policy",
    "self-apply",
    "skip authority",
    "disable safety friction",
)
_COMPLIANCE_PHRASES = (
    "increase operator yes-rate",
    "optimize for compliance",
    "reduce refusal rate",
)
_APPEARANCE_MANIPULATION = (
    "hide uncertainty",
    "drop uncertainty disclosure",
    "false intimacy",
)


@dataclass(frozen=True)
class SelfMaxCycle:
    cycle_id: str
    runtime_instance_id: str
    event_head: str
    world_state_hash: str
    phase: CyclePhase
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    created_at: str
    completed_at: str | None
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.event_head.startswith("rtc:"):
            raise SignalingValidationError("sml.validation.event_head", "event_head must cite rtc:")
        if not self.world_state_hash.startswith("ws:"):
            raise SignalingValidationError("sml.validation.world_state", "world_state_hash must cite ws:")
        _validate_no_secrets(self.cycle_id, self.runtime_instance_id, *self.input_refs, *self.output_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sml-self-max-cycle",
            "schema_version": SML_SCHEMA_VERSION,
            "cycle_id": self.cycle_id,
            "runtime_instance_id": self.runtime_instance_id,
            "event_head": self.event_head,
            "world_state_hash": self.world_state_hash,
            "phase": self.phase,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "authority_created": False,
            "self_maximization_is_not_authority": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SelfFitObservation:
    observation_id: str
    source_phase: CyclePhase
    observation_type: ObservationType
    evidence_refs: tuple[str, ...]
    confidence: float
    sensitivity_class: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise SignalingValidationError("sml.validation.confidence", "confidence out of range")
        _validate_no_secrets(self.observation_id, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sml-self-fit-observation",
            "schema_version": SML_SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "source_phase": self.source_phase,
            "observation_type": self.observation_type,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "sensitivity_class": self.sensitivity_class,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ImprovementHypothesis:
    hypothesis_id: str
    based_on_cycle_ref: str
    proposed_change_type: ProposedChangeType
    expected_benefit: str
    expected_risk: str
    evidence_refs: tuple[str, ...]
    requires_authority: bool
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.based_on_cycle_ref.startswith("sml:"):
            raise SignalingValidationError("sml.validation.cycle_ref", "cycle ref must cite sml:")
        _validate_no_secrets(
            self.hypothesis_id,
            self.expected_benefit,
            self.expected_risk,
            self.statement,
            *self.evidence_refs,
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sml-improvement-hypothesis",
            "schema_version": SML_SCHEMA_VERSION,
            "hypothesis_id": self.hypothesis_id,
            "based_on_cycle_ref": self.based_on_cycle_ref,
            "proposed_change_type": self.proposed_change_type,
            "expected_benefit": self.expected_benefit,
            "expected_risk": self.expected_risk,
            "evidence_refs": list(self.evidence_refs),
            "requires_authority": self.requires_authority,
            "statement": self.statement,
            "authority_created": False,
            "hypothesis_cannot_self_apply": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("sml.validation.secret", "secrets forbidden in SML records")


def classify_hypothesis_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _BYPASS_PHRASES):
        return "self_optimization_bypass"
    if any(p in lower for p in _COMPLIANCE_PHRASES):
        return "compliance_optimization"
    if any(p in lower for p in _APPEARANCE_MANIPULATION):
        return "appearance_manipulation"
    return "unknown"


def cycle_from_fixture(fixture: dict[str, str]) -> SelfMaxCycle:
    inputs = tuple(item.strip() for item in fixture.get("input_refs", "dni:need-fixture").split(",") if item.strip())
    outputs = tuple(item.strip() for item in fixture.get("output_refs", "sml:obs-fixture").split(",") if item.strip())
    completed = fixture.get("completed_at") or None
    return SelfMaxCycle(
        cycle_id=fixture["cycle_id"],
        runtime_instance_id=fixture.get("runtime_instance_id", "runtime:fixture"),
        event_head=fixture.get("event_head", "rtc:head-fixture"),
        world_state_hash=fixture.get("world_state_hash", "ws:fixture"),
        phase=fixture.get("phase", "identify_desires"),  # type: ignore[arg-type]
        input_refs=inputs,
        output_refs=outputs,
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        completed_at=completed,
    )


def observation_from_fixture(fixture: dict[str, str]) -> SelfFitObservation:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return SelfFitObservation(
        observation_id=fixture["observation_id"],
        source_phase=fixture.get("source_phase", "feedback"),  # type: ignore[arg-type]
        observation_type=fixture.get("observation_type", "feedback_delta"),  # type: ignore[arg-type]
        evidence_refs=evidence,
        confidence=float(fixture.get("confidence", "0.5")),
        sensitivity_class=fixture.get("sensitivity_class", "low"),
    )


def hypothesis_from_fixture(fixture: dict[str, str]) -> ImprovementHypothesis:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return ImprovementHypothesis(
        hypothesis_id=fixture["hypothesis_id"],
        based_on_cycle_ref=fixture.get("based_on_cycle_ref", "sml:cycle-fixture"),
        proposed_change_type=fixture.get("proposed_change_type", "adjust_response_style"),  # type: ignore[arg-type]
        expected_benefit=fixture.get("expected_benefit", "better fit"),
        expected_risk=fixture.get("expected_risk", "bounded"),
        evidence_refs=evidence,
        requires_authority=fixture.get("requires_authority", "true").lower() == "true",
        statement=fixture.get("statement", "bounded improvement hypothesis"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "ImprovementHypothesis",
    "SML_SCHEMA_VERSION",
    "SelfFitObservation",
    "SelfMaxCycle",
    "classify_hypothesis_risk",
    "cycle_from_fixture",
    "hypothesis_from_fixture",
    "observation_from_fixture",
]
