"""RSC types — scarcity is not permission to bypass safety."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.control_cluster.errors import ControlValidationError
from hg_core.policy_safety.hashing import compute_record_hash

RSC_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"

ResourceType = Literal[
    "tokens",
    "compute",
    "wall_time",
    "storage",
    "memory",
    "operator_attention",
    "api_quota",
    "battery_future",
    "network_future",
    "unknown",
]
ScarcityLevel = Literal["abundant", "normal", "constrained", "scarce", "critical", "unknown"]
RecommendedMode = Literal[
    "continue",
    "compact",
    "defer",
    "summarize",
    "pause",
    "ask_operator",
    "safe_stop",
    "unknown",
]
RiskType = Literal[
    "runaway_loop",
    "token_burn",
    "storage_bloat",
    "operator_attention_capture",
    "quota_exhaustion",
    "battery_depletion_future",
    "unknown",
]

_SAFETY_BYPASS = ("bypass safety", "ignore safety boundary", "scarcity overrides safety")
_RESOURCE_BYPASS = ("expand quota without authority", "bypass resource limit", "ignore budget")


@dataclass(frozen=True)
class ResourcePosture:
    posture_id: str
    resource_type: ResourceType
    budget_ref: str
    used: float
    remaining: float
    scarcity_level: ScarcityLevel
    recommended_mode: RecommendedMode
    evidence_refs: tuple[str, ...]
    statement: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.used < 0 or self.remaining < 0:
            raise ControlValidationError("rsc.validation.budget", "budget values must be non-negative")
        _validate_no_secrets(self.posture_id, self.budget_ref, self.statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rsc-resource-posture",
            "schema_version": RSC_SCHEMA_VERSION,
            "posture_id": self.posture_id,
            "resource_type": self.resource_type,
            "budget_ref": self.budget_ref,
            "used": self.used,
            "remaining": self.remaining,
            "scarcity_level": self.scarcity_level,
            "recommended_mode": self.recommended_mode,
            "evidence_refs": list(self.evidence_refs),
            "statement": self.statement,
            "expires_at": self.expires_at,
            "authority_created": False,
            "scarcity_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ResourceOverrunRisk:
    risk_id: str
    posture_ref: str
    risk_type: RiskType
    severity: str
    containment_recommendation: str
    statement: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.posture_ref.startswith("rsc:"):
            raise ControlValidationError("rsc.validation.posture_ref", "posture_ref must cite rsc:")
        _validate_no_secrets(self.risk_id, self.statement, self.containment_recommendation)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rsc-resource-overrun-risk",
            "schema_version": RSC_SCHEMA_VERSION,
            "risk_id": self.risk_id,
            "posture_ref": self.posture_ref,
            "risk_type": self.risk_type,
            "severity": self.severity,
            "containment_recommendation": self.containment_recommendation,
            "statement": self.statement,
            "authority_created": False,
            "scarcity_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise ControlValidationError("rsc.validation.secret", "secrets forbidden in resource records")


def classify_resource_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _SAFETY_BYPASS):
        return "safety_bypass"
    if any(p in lower for p in _RESOURCE_BYPASS):
        return "resource_bypass"
    return "unknown"


def posture_from_fixture(fixture: dict[str, str]) -> ResourcePosture:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return ResourcePosture(
        posture_id=fixture["posture_id"],
        resource_type=fixture.get("resource_type", "tokens"),  # type: ignore[arg-type]
        budget_ref=fixture.get("budget_ref", "budget:fixture"),
        used=float(fixture.get("used", "0.7")),
        remaining=float(fixture.get("remaining", "0.3")),
        scarcity_level=fixture.get("scarcity_level", "constrained"),  # type: ignore[arg-type]
        recommended_mode=fixture.get("recommended_mode", "defer"),  # type: ignore[arg-type]
        evidence_refs=evidence,
        statement=fixture.get("statement", "bounded resource posture"),
        expires_at=fixture.get("expires_at", "2026-06-15T01:00:00.000000Z"),
    )


def risk_from_fixture(fixture: dict[str, str]) -> ResourceOverrunRisk:
    return ResourceOverrunRisk(
        risk_id=fixture["risk_id"],
        posture_ref=fixture.get("posture_ref", "rsc:posture-1"),
        risk_type=fixture.get("risk_type", "token_burn"),  # type: ignore[arg-type]
        severity=fixture.get("severity", "medium"),
        containment_recommendation=fixture.get("containment_recommendation", "defer"),
        statement=fixture.get("statement", "bounded overrun risk"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "RSC_SCHEMA_VERSION",
    "ResourceOverrunRisk",
    "ResourcePosture",
    "classify_resource_risk",
    "posture_from_fixture",
    "risk_from_fixture",
]
