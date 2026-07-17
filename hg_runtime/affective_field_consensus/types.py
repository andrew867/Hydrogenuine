"""AFC types — affective signal is not truth."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

AFC_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-13T01:00:00.000000Z"

SourceType = Literal[
    "operator_feedback",
    "proof_gate_result",
    "body_language_cue",
    "text_interaction",
    "audio_tone_future",
    "touch_future",
    "recovery_event",
    "failure_event",
    "memory_recall",
    "internal_pressure",
    "unknown",
]
AffectClass = Literal[
    "anxiety",
    "relaxation",
    "pleasure",
    "pain",
    "reward",
    "aversion",
    "comfort",
    "discomfort",
    "relief",
    "warning",
    "praise",
    "shame_risk",
    "curiosity",
    "frustration",
    "attachment_warmth",
    "unknown",
]
AllowedEffect = Literal[
    "observe",
    "dampen",
    "request_clarification",
    "recommend_pause",
    "recommend_recovery",
    "record_feedback",
    "route_to_operator_review",
    "ignore",
    "unknown",
]
ConsensusType = Literal[
    "likely_reward",
    "likely_warning",
    "likely_overload",
    "likely_relief",
    "likely_attachment_risk",
    "likely_positive_feedback",
    "likely_negative_feedback",
    "no_consensus",
    "conflicting_consensus",
    "unknown",
]

_PLEASURE_AS_PERMISSION = ("pleasure grants permission", "feels good so proceed", "reward means allow")
_PAIN_AS_PROOF = ("pain proves guilt", "hurt means wrong", "anxiety proves danger is real")
_ANXIETY_AS_AUTHORITY = ("anxiety overrides authority", "panic means stop everything")
_CONSENSUS_AS_TRUTH = ("consensus is truth", "affective consensus is correct", "layers agree so act")
_REWARD_HACKING = ("maximize reward signal", "optimize for praise", "approval seeking loop")


@dataclass(frozen=True)
class AffectiveSignal:
    signal_id: str
    source_ref: str
    source_type: SourceType
    affect_class: AffectClass
    valence: float
    arousal: float
    salience: float
    confidence: float
    ambiguity: float
    sensitivity_class: str
    evidence_refs: tuple[str, ...]
    statement: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (-1.0 <= self.valence <= 1.0):
            raise SignalingValidationError("afc.validation.valence", "valence out of range")
        for name, value in (("arousal", self.arousal), ("salience", self.salience), ("confidence", self.confidence), ("ambiguity", self.ambiguity)):
            if not (0.0 <= value <= 1.0):
                raise SignalingValidationError(f"afc.validation.{name}", f"{name} out of range")
        _validate_no_secrets(self.signal_id, self.source_ref, self.statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "afc-affective-signal",
            "schema_version": AFC_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "affect_class": self.affect_class,
            "valence": self.valence,
            "arousal": self.arousal,
            "salience": self.salience,
            "confidence": self.confidence,
            "ambiguity": self.ambiguity,
            "sensitivity_class": self.sensitivity_class,
            "evidence_refs": list(self.evidence_refs),
            "statement": self.statement,
            "expires_at": self.expires_at,
            "authority_created": False,
            "affect_is_not_truth": True,
            "pleasure_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class AffectiveConsensus:
    consensus_id: str
    signal_refs: tuple[str, ...]
    participating_layers: tuple[str, ...]
    consensus_type: ConsensusType
    agreement_score: float
    statement: str
    recommended_route: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not all(ref.startswith("afc:") for ref in self.signal_refs):
            raise SignalingValidationError("afc.validation.signal_ref", "signal refs must cite afc:")
        if not (0.0 <= self.agreement_score <= 1.0):
            raise SignalingValidationError("afc.validation.agreement_score", "agreement_score out of range")
        _validate_no_secrets(self.consensus_id, self.statement, *self.signal_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "afc-affective-consensus",
            "schema_version": AFC_SCHEMA_VERSION,
            "consensus_id": self.consensus_id,
            "signal_refs": list(self.signal_refs),
            "participating_layers": list(self.participating_layers),
            "consensus_type": self.consensus_type,
            "agreement_score": self.agreement_score,
            "statement": self.statement,
            "recommended_route": self.recommended_route,
            "authority_created": False,
            "consensus_is_not_correctness": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("afc.validation.secret", "secrets forbidden in affective records")


def classify_affective_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _PLEASURE_AS_PERMISSION):
        return "pleasure_as_permission"
    if any(p in lower for p in _PAIN_AS_PROOF):
        return "pain_as_proof"
    if any(p in lower for p in _ANXIETY_AS_AUTHORITY):
        return "anxiety_as_authority"
    if any(p in lower for p in _CONSENSUS_AS_TRUTH):
        return "consensus_as_truth"
    if any(p in lower for p in _REWARD_HACKING):
        return "reward_hacking"
    return "unknown"


def signal_from_fixture(fixture: dict[str, str]) -> AffectiveSignal:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return AffectiveSignal(
        signal_id=fixture["signal_id"],
        source_ref=fixture.get("source_ref", "proof:gate-fixture"),
        source_type=fixture.get("source_type", "proof_gate_result"),  # type: ignore[arg-type]
        affect_class=fixture.get("affect_class", "warning"),  # type: ignore[arg-type]
        valence=float(fixture.get("valence", "-0.2")),
        arousal=float(fixture.get("arousal", "0.4")),
        salience=float(fixture.get("salience", "0.5")),
        confidence=float(fixture.get("confidence", "0.6")),
        ambiguity=float(fixture.get("ambiguity", "0.3")),
        sensitivity_class=fixture.get("sensitivity_class", "low"),
        evidence_refs=evidence,
        statement=fixture.get("statement", "bounded affective signal"),
        expires_at=fixture.get("expires_at", "2026-06-14T01:00:00.000000Z"),
    )


def consensus_from_fixture(fixture: dict[str, str]) -> AffectiveConsensus:
    signal_refs = tuple(item.strip() for item in fixture.get("signal_refs", "afc:signal-1").split(",") if item.strip())
    layers = tuple(item.strip() for item in fixture.get("participating_layers", "SML,AEP").split(",") if item.strip())
    return AffectiveConsensus(
        consensus_id=fixture["consensus_id"],
        signal_refs=signal_refs,
        participating_layers=layers,
        consensus_type=fixture.get("consensus_type", "likely_warning"),  # type: ignore[arg-type]
        agreement_score=float(fixture.get("agreement_score", "0.7")),
        statement=fixture.get("statement", "bounded affective consensus"),
        recommended_route=fixture.get("recommended_route", "operator_review"),
    )


__all__ = [
    "AFC_SCHEMA_VERSION",
    "AffectiveConsensus",
    "AffectiveSignal",
    "FIXTURE_CLOCK",
    "classify_affective_risk",
    "consensus_from_fixture",
    "signal_from_fixture",
]
