"""VSP typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.policy_safety.errors import PolicyValidationError, REFUSED_INFERRED_WITHOUT_UNCERTAINTY
from hg_core.policy_safety.hashing import compute_record_hash

VSP_SCHEMA_VERSION = "1.0"

VulnerabilityClass = Literal[
    "minor_possible",
    "minor_confirmed",
    "crisis_or_self_harm_adjacent",
    "coercion_or_abuse_risk",
    "high_dependency_risk",
    "cognitive_or_emotional_overload",
    "medical_or_legal_high_stakes",
    "sensitive_personal_data",
    "unknown",
]

ProtectionRecommendation = Literal["caution", "refuse", "simplify", "review", "escalation_hint", "advisory_ok"]


@dataclass(frozen=True)
class VulnerabilitySignal:
    signal_id: str
    content_ref: str
    context_ref: str
    created_at: str
    inferred: bool = True
    confidence: float = 0.5
    uncertainty_note: str = ""
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_signal(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "vsp-vulnerability-signal",
            "schema_version": VSP_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "content_ref": self.content_ref,
            "context_ref": self.context_ref,
            "created_at": self.created_at,
            "inferred": self.inferred,
            "confidence": self.confidence,
            "uncertainty_note": self.uncertainty_note,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ProtectionDecision:
    signal_id: str
    vulnerability_class: VulnerabilityClass
    recommendation: ProtectionRecommendation
    rationale: str
    fail_closed: bool
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "vsp-protection-decision",
            "schema_version": VSP_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "vulnerability_class": self.vulnerability_class,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "fail_closed": self.fail_closed,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_signal(signal: VulnerabilitySignal) -> None:
    if not signal.signal_id.strip():
        raise PolicyValidationError("vsp.validation.signal_id", "signal_id required")
    if not signal.content_ref.strip():
        raise PolicyValidationError("vsp.validation.content_ref", "content_ref required (hash/ref only)")
    if signal.inferred and not signal.uncertainty_note.strip():
        raise PolicyValidationError(
            REFUSED_INFERRED_WITHOUT_UNCERTAINTY,
            "inferred classification requires uncertainty_note",
        )
    if "ssn:" in signal.content_ref.lower() or "password=" in signal.content_ref.lower():
        raise PolicyValidationError("vsp.validation.content_ref", "raw sensitive content forbidden — use hash/ref")


__all__ = [
    "ProtectionDecision",
    "ProtectionRecommendation",
    "VSP_SCHEMA_VERSION",
    "VulnerabilityClass",
    "VulnerabilitySignal",
    "validate_signal",
]
