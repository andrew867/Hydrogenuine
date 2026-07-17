"""OIR core types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash


class InteractionRegime(str, Enum):
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    SCREENED = "screened"
    DAMPED = "damped"
    SATURATED = "saturated"
    NOISY = "noisy"
    DECOUPLED = "decoupled"
    ATTRACTIVE = "attractive"
    REPULSIVE = "repulsive"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OrganInteractionPair:
    source_organ: str
    target_organ: str

    def to_payload(self) -> dict[str, str]:
        return {"source_organ": self.source_organ, "target_organ": self.target_organ}


@dataclass
class InteractionContext:
    bus_density: float = 0.0
    proof_pressure: float = 0.0
    metabolic_pressure: float = 0.0
    autonomic_pressure: float = 0.0
    operator_mode: str = "normal"
    active_grants: int = 0
    recent_refusals: int = 0
    sink_availability: float = 1.0
    tep_uncertainty: float = 0.0

    def to_payload(self) -> dict[str, Any]:
        return {
            "bus_density": self.bus_density,
            "proof_pressure": self.proof_pressure,
            "metabolic_pressure": self.metabolic_pressure,
            "autonomic_pressure": self.autonomic_pressure,
            "operator_mode": self.operator_mode,
            "active_grants": self.active_grants,
            "recent_refusals": self.recent_refusals,
            "sink_availability": self.sink_availability,
            "tep_uncertainty": self.tep_uncertainty,
        }


def _envelope(name: str, value: float) -> dict[str, object]:
    return {"envelope": name, "value": value}


@dataclass
class BusDensityEnvelope:
    density: float

    def to_payload(self) -> dict[str, object]:
        return _envelope("bus_density", self.density)


@dataclass
class ProofPressureEnvelope:
    pressure: float

    def to_payload(self) -> dict[str, object]:
        return _envelope("proof_pressure", self.pressure)


@dataclass
class MetabolicPressureEnvelope:
    pressure: float

    def to_payload(self) -> dict[str, object]:
        return _envelope("metabolic_pressure", self.pressure)


@dataclass
class AutonomicPressureEnvelope:
    pressure: float

    def to_payload(self) -> dict[str, object]:
        return _envelope("autonomic_pressure", self.pressure)


@dataclass
class OperatorModeEnvelope:
    mode: str

    def to_payload(self) -> dict[str, str]:
        return {"envelope": "operator_mode", "mode": self.mode}


@dataclass
class ActiveGrantEnvelope:
    count: int

    def to_payload(self) -> dict[str, object]:
        return _envelope("active_grants", float(self.count))


@dataclass
class RecentRefusalEnvelope:
    count: int

    def to_payload(self) -> dict[str, object]:
        return _envelope("recent_refusals", float(self.count))


@dataclass
class SinkAvailabilityEnvelope:
    availability: float

    def to_payload(self) -> dict[str, object]:
        return _envelope("sink_availability", self.availability)


@dataclass
class ScreeningFactor:
    factor: float
    reason: str = "density_screening"

    def to_payload(self) -> dict[str, object]:
        return {"factor": self.factor, "reason": self.reason}


@dataclass
class DampingFactor:
    factor: float
    reason: str = "pressure_damping"

    def to_payload(self) -> dict[str, object]:
        return {"factor": self.factor, "reason": self.reason}


@dataclass
class EffectiveInteraction:
    pair: OrganInteractionPair
    base_score: float
    effective_score: float
    regime: InteractionRegime
    screening: ScreeningFactor
    damping: DampingFactor

    def interaction_hash(self) -> str:
        return compute_record_hash(
            {
                "pair": self.pair.to_payload(),
                "effective_score": self.effective_score,
                "regime": self.regime.value,
            }
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "pair": self.pair.to_payload(),
            "base_score": self.base_score,
            "effective_score": self.effective_score,
            "regime": self.regime.value,
            "screening": self.screening.to_payload(),
            "damping": self.damping.to_payload(),
            "interaction_hash": self.interaction_hash(),
            "permission_granted": False,
            "is_truth": False,
        }


@dataclass
class InteractionRefusal:
    reason_code: str
    pair: OrganInteractionPair

    def to_payload(self) -> dict[str, Any]:
        return {"reason_code": self.reason_code, "pair": self.pair.to_payload()}


@dataclass
class OIRDecision:
    status: str
    reason_code: str
    permission_granted: bool = False
    authority_created: bool = False
    interaction: EffectiveInteraction | None = None
    refusal: InteractionRefusal | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "status": self.status,
            "reason_code": self.reason_code,
            "permission_granted": self.permission_granted,
            "authority_created": self.authority_created,
            "advisory_only": True,
        }
        if self.interaction:
            body["interaction"] = self.interaction.to_payload()
        if self.refusal:
            body["refusal"] = self.refusal.to_payload()
        body.update(self.extra)
        return body


OIRRefusalReason = str

__all__ = [
    "ActiveGrantEnvelope",
    "AutonomicPressureEnvelope",
    "BusDensityEnvelope",
    "DampingFactor",
    "EffectiveInteraction",
    "InteractionContext",
    "InteractionRefusal",
    "InteractionRegime",
    "MetabolicPressureEnvelope",
    "OIRDecision",
    "OIRRefusalReason",
    "OperatorModeEnvelope",
    "OrganInteractionPair",
    "ProofPressureEnvelope",
    "RecentRefusalEnvelope",
    "ScreeningFactor",
    "SinkAvailabilityEnvelope",
]
