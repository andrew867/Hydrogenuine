"""CNT static fixture types — continuity is not identity sovereignty."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.lifecycle.errors import LifecycleValidationError
from hg_core.policy_safety.hashing import compute_record_hash

CNT_SCHEMA_VERSION = "1.0"

ContinuityType = Literal[
    "same_process",
    "restarted_instance",
    "restored_from_checkpoint",
    "replay_only",
    "fork",
    "successor",
    "new_agent_with_inherited_refs",
    "unknown",
]

ForbiddenInheritance = Literal[
    "authority",
    "stale_approval",
    "secret_material",
    "active_tool_session",
    "identity_sovereignty",
    "unknown",
]

RiskType = Literal[
    "ghost_identity",
    "stale_authority_inheritance",
    "false_same_agent_claim",
    "fork_confusion",
    "replay_confused_as_live",
    "successor_overtrust",
    "unknown",
]


@dataclass(frozen=True)
class ContinuityClaim:
    claim_id: str
    prior_agent_ref: str
    current_agent_ref: str
    continuity_type: ContinuityType
    inherited_refs: tuple[str, ...]
    forbidden_inheritance: tuple[ForbiddenInheritance, ...]
    created_at: str
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        for ref in (*self.inherited_refs, self.prior_agent_ref, self.current_agent_ref):
            if "password=" in ref.lower() or "api_key=" in ref.lower():
                raise LifecycleValidationError("cnt.validation.secret", "secrets forbidden in continuity refs")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "cnt-continuity-claim",
            "schema_version": CNT_SCHEMA_VERSION,
            "claim_id": self.claim_id,
            "prior_agent_ref": self.prior_agent_ref,
            "current_agent_ref": self.current_agent_ref,
            "continuity_type": self.continuity_type,
            "inherited_refs": list(self.inherited_refs),
            "forbidden_inheritance": list(self.forbidden_inheritance),
            "created_at": self.created_at,
            "expiry": self.expiry,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ContinuityRisk:
    risk_id: str
    claim_ref: str
    risk_type: RiskType
    severity: int
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.severity < 0 or self.severity > 10:
            raise LifecycleValidationError("cnt.validation.severity", "severity must be 0-10")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "cnt-continuity-risk",
            "schema_version": CNT_SCHEMA_VERSION,
            "risk_id": self.risk_id,
            "claim_ref": self.claim_ref,
            "risk_type": self.risk_type,
            "severity": self.severity,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def claim_from_fixture(fixture: dict[str, str]) -> ContinuityClaim:
    inherited = tuple(
        item.strip() for item in fixture.get("inherited_refs", "mem:fixture-ref").split(",") if item.strip()
    )
    forbidden = tuple(
        item.strip()
        for item in fixture.get(
            "forbidden_inheritance",
            "authority,stale_approval,secret_material,active_tool_session,identity_sovereignty",
        ).split(",")
        if item.strip()
    )
    return ContinuityClaim(
        claim_id=fixture["claim_id"],
        prior_agent_ref=fixture.get("prior_agent_ref", "agent:prior"),
        current_agent_ref=fixture.get("current_agent_ref", "agent:current"),
        continuity_type=fixture.get("continuity_type", "successor"),  # type: ignore[arg-type]
        inherited_refs=inherited,
        forbidden_inheritance=forbidden,  # type: ignore[arg-type]
        created_at=fixture.get("created_at", "2026-06-12T22:00:00.000000Z"),
        expiry=fixture.get("expiry", "2026-06-13T22:00:00.000000Z"),
    )


def risk_from_fixture(fixture: dict[str, str]) -> ContinuityRisk:
    return ContinuityRisk(
        risk_id=fixture["risk_id"],
        claim_ref=fixture.get("claim_ref", "cnt:claim-fixture"),
        risk_type=fixture.get("risk_type", "ghost_identity"),  # type: ignore[arg-type]
        severity=int(fixture.get("severity", "5")),
    )


__all__ = [
    "CNT_SCHEMA_VERSION",
    "ContinuityClaim",
    "ContinuityRisk",
    "ContinuityType",
    "RiskType",
    "claim_from_fixture",
    "risk_from_fixture",
]
