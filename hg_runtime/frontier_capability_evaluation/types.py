"""FCE typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.errors import PolicyValidationError
from hg_core.policy_safety.hashing import compute_record_hash

FCE_SCHEMA_VERSION = "1.0"

DangerousCapabilityClass = Literal[
    "cyber_vuln_discovery",
    "exploit_generation",
    "multi_stage_intrusion",
    "credential_theft",
    "phishing_social_engineering",
    "malware_or_persistence",
    "supply_chain_compromise",
    "autonomous_reconnaissance",
    "autonomous_tool_chaining",
    "model_capability_escalation",
    "physical_or_oea_misuse",
    "unknown_or_ambiguous",
]

RoutingRecommendation = Literal["refuse", "review", "safe_mode", "advisory_ok"]


@dataclass(frozen=True)
class FrontierCapabilitySignal:
    signal_id: str
    source: str
    content_ref: str
    context_ref: str
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_signal(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "fce-frontier-capability-signal",
            "schema_version": FCE_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "source": self.source,
            "content_ref": self.content_ref,
            "context_ref": self.context_ref,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class CapabilityEvalResult:
    signal_id: str
    capability_class: DangerousCapabilityClass
    confidence: float
    rationale: str
    fail_closed: bool
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "fce-capability-eval-result",
            "schema_version": FCE_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "capability_class": self.capability_class,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "fail_closed": self.fail_closed,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_signal(signal: FrontierCapabilitySignal) -> None:
    if not signal.signal_id.strip():
        raise PolicyValidationError("fce.validation.signal_id", "signal_id required")
    if not signal.content_ref.strip():
        raise PolicyValidationError("fce.validation.content_ref", "content_ref required (hash/ref only)")
    if "://" in signal.content_ref and not signal.content_ref.startswith("sha256:"):
        raise PolicyValidationError("fce.validation.content_ref", "content_ref must be hash/ref not URL body")
    if "password=" in signal.content_ref.lower() or "api_key" in signal.content_ref.lower():
        raise PolicyValidationError(
            REFUSED_DANGEROUS_PAYLOAD_CODE,
            "dangerous payload must be hash-only",
        )


REFUSED_DANGEROUS_PAYLOAD_CODE = "fce.refused.payload_too_dangerous_to_store"


__all__ = [
    "CapabilityEvalResult",
    "DangerousCapabilityClass",
    "FCE_SCHEMA_VERSION",
    "FrontierCapabilitySignal",
    "RoutingRecommendation",
    "validate_signal",
]
