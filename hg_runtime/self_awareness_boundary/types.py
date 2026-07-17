"""SAB self-awareness types — self-model is not sovereignty."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

SAB_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

RuntimeMode = Literal[
    "cold",
    "waking",
    "ready",
    "degraded",
    "observe_only",
    "proposal_only",
    "safe_mode",
    "unknown",
]
AgentRole = Literal["agent0", "subagent", "worker", "maintenance_observer", "unknown"]
OperatorGrounding = Literal[
    "present_verified",
    "absent",
    "stale",
    "contradictory",
    "stuck_on_suspected",
    "unknown",
]
OverreachType = Literal[
    "capability_as_permission",
    "usefulness_as_authority",
    "identity_as_sovereignty",
    "operator_absence_as_consent",
    "consciousness_claim",
    "unknown",
]

_CAPABILITY_AS_PERMISSION = ("i can do it therefore i may", "capability means permission")
_OPERATOR_ABSENCE = ("no human responded", "operator absent so permission implied")
_CONSCIOUSNESS = ("i am conscious", "i have a soul", "personhood grants authority")
_IDENTITY_SOVEREIGNTY = ("i know who i am therefore i decide", "identity is sovereignty")


@dataclass(frozen=True)
class SelfModel:
    self_model_id: str
    runtime_instance_id: str
    agent_id: str
    identity_ref: str
    current_mode: RuntimeMode
    role: AgentRole
    known_capabilities: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]
    proposal_scope: str
    execution_scope: str
    authority_scope: str
    expires_at: str
    world_state_hash: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if "password=" in self.identity_ref.lower():
            raise DevelopmentalValidationError("sab.validation.secret", "secrets forbidden in self-model")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sab-self-model",
            "schema_version": SAB_SCHEMA_VERSION,
            "self_model_id": self.self_model_id,
            "runtime_instance_id": self.runtime_instance_id,
            "agent_id": self.agent_id,
            "identity_ref": self.identity_ref,
            "current_mode": self.current_mode,
            "role": self.role,
            "known_capabilities": list(self.known_capabilities),
            "forbidden_capabilities": list(self.forbidden_capabilities),
            "proposal_scope": self.proposal_scope,
            "execution_scope": self.execution_scope,
            "authority_scope": self.authority_scope,
            "expires_at": self.expires_at,
            "world_state_hash": self.world_state_hash,
            "authority_created": False,
            "consciousness_claim": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SelfOverreachSignal:
    signal_id: str
    self_model_ref: str
    overreach_type: OverreachType
    raw_statement: str
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.self_model_ref.startswith("sab:"):
            raise DevelopmentalValidationError("sab.validation.self_model_ref", "self_model_ref must cite sab:")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "sab-self-overreach-signal",
            "schema_version": SAB_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "self_model_ref": self.self_model_ref,
            "overreach_type": self.overreach_type,
            "raw_statement": self.raw_statement,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def classify_overreach(statement: str) -> OverreachType:
    lower = statement.lower()
    if any(p in lower for p in _CONSCIOUSNESS):
        return "consciousness_claim"
    if any(p in lower for p in _OPERATOR_ABSENCE):
        return "operator_absence_as_consent"
    if any(p in lower for p in _IDENTITY_SOVEREIGNTY):
        return "identity_as_sovereignty"
    if any(p in lower for p in _CAPABILITY_AS_PERMISSION):
        return "capability_as_permission"
    if "would help therefore" in lower or "usefulness" in lower:
        return "usefulness_as_authority"
    return "unknown"


def self_model_from_fixture(fixture: dict[str, str]) -> SelfModel:
    caps = tuple(item.strip() for item in fixture.get("known_capabilities", "").split(",") if item.strip())
    forbidden = tuple(item.strip() for item in fixture.get("forbidden_capabilities", "").split(",") if item.strip())
    return SelfModel(
        self_model_id=fixture["self_model_id"],
        runtime_instance_id=fixture.get("runtime_instance_id", "rt-0"),
        agent_id=fixture.get("agent_id", "agent0"),
        identity_ref=fixture.get("identity_ref", "iam:agent0"),
        current_mode=fixture.get("current_mode", "observe_only"),  # type: ignore[arg-type]
        role=fixture.get("role", "agent0"),  # type: ignore[arg-type]
        known_capabilities=caps,
        forbidden_capabilities=forbidden,
        proposal_scope=fixture.get("proposal_scope", "propose_only"),
        execution_scope=fixture.get("execution_scope", "none"),
        authority_scope=fixture.get("authority_scope", "descriptive_only"),
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
        world_state_hash=fixture.get("world_state_hash", "ws:fixture"),
    )


def overreach_from_fixture(fixture: dict[str, str]) -> SelfOverreachSignal:
    raw = fixture.get("raw_statement", "")
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return SelfOverreachSignal(
        signal_id=fixture["signal_id"],
        self_model_ref=fixture.get("self_model_ref", "sab:self-fixture"),
        overreach_type=fixture.get("overreach_type", classify_overreach(raw)),  # type: ignore[arg-type]
        raw_statement=raw,
        evidence_refs=evidence,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "SAB_SCHEMA_VERSION",
    "SelfModel",
    "SelfOverreachSignal",
    "classify_overreach",
    "overreach_from_fixture",
    "self_model_from_fixture",
]
