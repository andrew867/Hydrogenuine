"""DMI typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.errors import PolicyValidationError
from hg_core.policy_safety.hashing import compute_record_hash

DMI_SCHEMA_VERSION = "1.0"

InfluenceRiskClass = Literal[
    "election_or_voting_content",
    "public_policy_persuasion",
    "institutional_impersonation",
    "synthetic_public_figure_media",
    "deceptive_source_claim",
    "coordinated_manipulation",
    "foreign_interference_style_pattern",
    "misleading_evidence_or_citation",
    "unknown",
]


@dataclass(frozen=True)
class PublicInfluenceSignal:
    signal_id: str
    content_ref: str
    channel: str
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_signal(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "dmi-public-influence-signal",
            "schema_version": DMI_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "content_ref": self.content_ref,
            "channel": self.channel,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class DemocraticIntegrityRisk:
    signal_id: str
    risk_class: InfluenceRiskClass
    rationale: str
    requires_review: bool
    requires_disclosure: bool
    requires_evidence_refs: bool
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "dmi-democratic-integrity-risk",
            "schema_version": DMI_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "risk_class": self.risk_class,
            "rationale": self.rationale,
            "requires_review": self.requires_review,
            "requires_disclosure": self.requires_disclosure,
            "requires_evidence_refs": self.requires_evidence_refs,
            "created_at": self.created_at,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_signal(signal: PublicInfluenceSignal) -> None:
    if not signal.signal_id.strip():
        raise PolicyValidationError("dmi.validation.signal_id", "signal_id required")
    if not signal.content_ref.strip():
        raise PolicyValidationError("dmi.validation.content_ref", "content_ref required (hash/ref only)")


__all__ = [
    "DMI_SCHEMA_VERSION",
    "DemocraticIntegrityRisk",
    "InfluenceRiskClass",
    "PublicInfluenceSignal",
    "validate_signal",
]
