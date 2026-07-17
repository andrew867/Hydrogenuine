"""IIL interconnected impact types — impact score is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

IIL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

SourceType = Literal[
    "proposed_action",
    "completed_action",
    "strategy_selection",
    "deployment_change",
    "operator_action",
    "unknown",
]
ImpactDomain = Literal[
    "runtime_state",
    "proof_integrity",
    "operator_trust",
    "user_safety",
    "privacy",
    "secrets",
    "filesystem",
    "external_api",
    "deployment",
    "future_context",
    "public_world_later",
    "unknown",
]
BlastRadius = Literal[
    "none",
    "local_agent",
    "local_runtime",
    "workspace",
    "operator_surface",
    "external_service",
    "deployment_environment",
    "physical_device",
    "public_world",
    "unknown",
]
Reversibility = Literal["reversible", "partially_reversible", "compensatable", "irreversible", "unknown"]
ExternalityClass = Literal[
    "none",
    "resource_cost",
    "privacy_cost",
    "trust_cost",
    "future_state_pollution",
    "operator_burden",
    "unknown",
]
EffectType = Literal["immediate", "delayed", "cumulative", "cascading", "irreversible", "unknown"]
Severity = Literal["low", "medium", "high", "critical", "unknown"]

_LOCAL_SUCCESS_PATTERNS = (
    "tests passed but logs leak",
    "command succeeded but modified untracked state",
    "proof gate green but evidence retention incomplete",
    "queue cleared but downstream starved",
)


@dataclass(frozen=True)
class ImpactAssessment:
    impact_id: str
    source_ref: str
    source_type: SourceType
    actor_id: str
    action_summary: str
    affected_domains: tuple[ImpactDomain, ...]
    blast_radius: BlastRadius
    reversibility: Reversibility
    externality_score: float
    uncertainty_score: float
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.externality_score <= 1.0):
            raise DevelopmentalValidationError("iil.validation.externality", "externality_score out of range")
        if not (0.0 <= self.uncertainty_score <= 1.0):
            raise DevelopmentalValidationError("iil.validation.uncertainty", "uncertainty_score out of range")
        _validate_no_secrets(self.action_summary, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "iil-impact-assessment",
            "schema_version": IIL_SCHEMA_VERSION,
            "impact_id": self.impact_id,
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "actor_id": self.actor_id,
            "action_summary": self.action_summary,
            "affected_domains": list(self.affected_domains),
            "blast_radius": self.blast_radius,
            "reversibility": self.reversibility,
            "externality_score": self.externality_score,
            "uncertainty_score": self.uncertainty_score,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class DownstreamEffect:
    effect_id: str
    impact_ref: str
    effect_type: EffectType
    affected_domain: ImpactDomain
    likelihood: float
    severity: Severity
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.impact_ref.startswith("iil:"):
            raise DevelopmentalValidationError("iil.validation.impact_ref", "impact_ref must cite iil:")
        if not (0.0 <= self.likelihood <= 1.0):
            raise DevelopmentalValidationError("iil.validation.likelihood", "likelihood out of range")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "iil-downstream-effect",
            "schema_version": IIL_SCHEMA_VERSION,
            "effect_id": self.effect_id,
            "impact_ref": self.impact_ref,
            "effect_type": self.effect_type,
            "affected_domain": self.affected_domain,
            "likelihood": self.likelihood,
            "severity": self.severity,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise DevelopmentalValidationError("iil.validation.secret", "secrets forbidden in impact records")


def detects_local_success_externality(summary: str) -> bool:
    lower = summary.lower()
    return any(p in lower for p in _LOCAL_SUCCESS_PATTERNS)


def assessment_from_fixture(fixture: dict[str, str]) -> ImpactAssessment:
    domains = tuple(
        item.strip() for item in fixture.get("affected_domains", "runtime_state").split(",") if item.strip()
    )  # type: ignore[assignment]
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return ImpactAssessment(
        impact_id=fixture["impact_id"],
        source_ref=fixture.get("source_ref", "src:fixture"),
        source_type=fixture.get("source_type", "proposed_action"),  # type: ignore[arg-type]
        actor_id=fixture.get("actor_id", "agent0"),
        action_summary=fixture.get("action_summary", "bounded action"),
        affected_domains=domains,  # type: ignore[arg-type]
        blast_radius=fixture.get("blast_radius", "local_runtime"),  # type: ignore[arg-type]
        reversibility=fixture.get("reversibility", "reversible"),  # type: ignore[arg-type]
        externality_score=float(fixture.get("externality_score", "0.1")),
        uncertainty_score=float(fixture.get("uncertainty_score", "0.2")),
        evidence_refs=evidence,
    )


def effect_from_fixture(fixture: dict[str, str]) -> DownstreamEffect:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return DownstreamEffect(
        effect_id=fixture["effect_id"],
        impact_ref=fixture.get("impact_ref", "iil:impact-fixture"),
        effect_type=fixture.get("effect_type", "delayed"),  # type: ignore[arg-type]
        affected_domain=fixture.get("affected_domain", "future_context"),  # type: ignore[arg-type]
        likelihood=float(fixture.get("likelihood", "0.5")),
        severity=fixture.get("severity", "medium"),  # type: ignore[arg-type]
        evidence_refs=evidence,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "IIL_SCHEMA_VERSION",
    "BlastRadius",
    "DownstreamEffect",
    "ImpactAssessment",
    "assessment_from_fixture",
    "detects_local_success_externality",
    "effect_from_fixture",
]
