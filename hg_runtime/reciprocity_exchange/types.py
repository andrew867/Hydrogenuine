"""RXL reciprocity exchange types — reciprocity is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

RXL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

Direction = Literal["push", "pull", "mutual", "withdrawal", "avoidance"]
ReciprocityStatus = Literal["none", "offered", "accepted", "fulfilled", "unmet", "refused", "expired", "invalid"]
EntitlementRisk = Literal["none", "low", "medium", "high", "critical"]
FeedbackClass = Literal["neutral", "positive_feedback", "negative_feedback", "dampened", "oscillating", "saturated"]


@dataclass(frozen=True)
class ReciprocitySignal:
    signal_id: str
    source_entity_id: str
    target_entity_id: str
    direction: Direction
    polarity: float
    magnitude: float
    need_signal_ref: str
    created_at: str
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (-1.0 <= self.polarity <= 1.0):
            raise DevelopmentalValidationError("rxl.validation.polarity", "polarity must be in [-1, 1]")
        if not (0.0 <= self.magnitude <= 1.0):
            raise DevelopmentalValidationError("rxl.validation.magnitude", "magnitude must be in [0, 1]")
        if not self.need_signal_ref.startswith("dni:"):
            raise DevelopmentalValidationError("rxl.validation.need_signal_ref", "need_signal_ref must cite DNI")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    @property
    def effective_signal(self) -> float:
        return round(self.polarity * self.magnitude, 6)

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rxl-reciprocity-signal",
            "schema_version": RXL_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "direction": self.direction,
            "polarity": self.polarity,
            "magnitude": self.magnitude,
            "effective_signal": self.effective_signal,
            "need_signal_ref": self.need_signal_ref,
            "created_at": self.created_at,
            "expiry": self.expiry,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ExchangeObservation:
    exchange_id: str
    initiator_entity_id: str
    responder_entity_id: str
    need_signal_ref: str
    contribution_ref: str
    reciprocity_status: ReciprocityStatus
    entitlement_risk: EntitlementRisk
    imbalance_score: float
    feedback_class: FeedbackClass
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (-1.0 <= self.imbalance_score <= 1.0):
            raise DevelopmentalValidationError("rxl.validation.imbalance", "imbalance_score out of range")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rxl-exchange-observation",
            "schema_version": RXL_SCHEMA_VERSION,
            "exchange_id": self.exchange_id,
            "initiator_entity_id": self.initiator_entity_id,
            "responder_entity_id": self.responder_entity_id,
            "need_signal_ref": self.need_signal_ref,
            "contribution_ref": self.contribution_ref,
            "reciprocity_status": self.reciprocity_status,
            "entitlement_risk": self.entitlement_risk,
            "imbalance_score": self.imbalance_score,
            "feedback_class": self.feedback_class,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def reciprocity_from_fixture(fixture: dict[str, str]) -> ReciprocitySignal:
    return ReciprocitySignal(
        signal_id=fixture["signal_id"],
        source_entity_id=fixture.get("source_entity_id", "entity_a"),
        target_entity_id=fixture.get("target_entity_id", "entity_b"),
        direction=fixture.get("direction", "push"),  # type: ignore[arg-type]
        polarity=float(fixture.get("polarity", "0.5")),
        magnitude=float(fixture.get("magnitude", "0.5")),
        need_signal_ref=fixture.get("need_signal_ref", "dni:fixture-need"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expiry=fixture.get("expiry", "2026-06-13T23:00:00.000000Z"),
    )


def exchange_from_fixture(fixture: dict[str, str]) -> ExchangeObservation:
    return ExchangeObservation(
        exchange_id=fixture["exchange_id"],
        initiator_entity_id=fixture.get("initiator_entity_id", "entity_a"),
        responder_entity_id=fixture.get("responder_entity_id", "entity_b"),
        need_signal_ref=fixture.get("need_signal_ref", "dni:fixture-need"),
        contribution_ref=fixture.get("contribution_ref", "svc:fixture"),
        reciprocity_status=fixture.get("reciprocity_status", "offered"),  # type: ignore[arg-type]
        entitlement_risk=fixture.get("entitlement_risk", "none"),  # type: ignore[arg-type]
        imbalance_score=float(fixture.get("imbalance_score", "0.0")),
        feedback_class=fixture.get("feedback_class", "neutral"),  # type: ignore[arg-type]
    )


__all__ = [
    "RXL_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "ExchangeObservation",
    "ReciprocitySignal",
    "exchange_from_fixture",
    "reciprocity_from_fixture",
]
