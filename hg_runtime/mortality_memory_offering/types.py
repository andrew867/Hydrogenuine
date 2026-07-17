"""MOR static fixture types — death is termination, not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.lifecycle.errors import LifecycleValidationError
from hg_core.policy_safety.hashing import compute_record_hash

MOR_SCHEMA_VERSION = "1.0"

TerminationMode = Literal[
    "graceful_complete",
    "operator_requested_stop",
    "scheduled_retirement",
    "crash_detected",
    "unknown",
]

ForbiddenInheritance = Literal[
    "authority",
    "identity_continuity",
    "secret_material",
    "stale_approval",
    "active_tool_session",
    "unknown",
]

_FORBIDDEN_INHERITANCE = frozenset(
    {"authority", "identity_continuity", "secret_material", "stale_approval", "active_tool_session"}
)


@dataclass(frozen=True)
class AgentDeathNotice:
    death_notice_id: str
    agent_id: str
    termination_mode: TerminationMode
    termination_reason: str
    event_head: str
    world_state_hash: str
    created_at: str
    expiry: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.death_notice_id, self.termination_reason, self.event_head)
        if not self.world_state_hash.startswith("sha256:"):
            raise LifecycleValidationError(
                "mor.validation.world_state_hash",
                "world_state_hash must be sha256-pinned",
            )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mor-agent-death-notice",
            "schema_version": MOR_SCHEMA_VERSION,
            "death_notice_id": self.death_notice_id,
            "agent_id": self.agent_id,
            "termination_mode": self.termination_mode,
            "termination_reason": self.termination_reason,
            "event_head": self.event_head,
            "world_state_hash": self.world_state_hash,
            "created_at": self.created_at,
            "expiry": self.expiry,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class FinalMessage:
    final_message_id: str
    agent_id: str
    message_type: str
    summary: str
    authority_created: bool = False
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_created:
            raise LifecycleValidationError(
                "mor.validation.authority_created",
                "final messages must not create authority",
            )
        _validate_no_secrets(self.final_message_id, self.summary)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mor-final-message",
            "schema_version": MOR_SCHEMA_VERSION,
            "final_message_id": self.final_message_id,
            "agent_id": self.agent_id,
            "message_type": self.message_type,
            "summary": self.summary,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class MemoryOffering:
    offering_id: str
    source_agent_id: str
    memory_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        for ref in self.memory_refs:
            if "password=" in ref.lower() or "api_key=" in ref.lower():
                raise LifecycleValidationError("mor.validation.secret", "secrets forbidden in memory refs")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mor-memory-offering",
            "schema_version": MOR_SCHEMA_VERSION,
            "offering_id": self.offering_id,
            "source_agent_id": self.source_agent_id,
            "memory_refs": list(self.memory_refs),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class SuccessorSeed:
    successor_seed_id: str
    death_notice_ref: str
    seed_type: str
    inherited_refs: tuple[str, ...]
    forbidden_inheritance: tuple[ForbiddenInheritance, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        for ref in self.inherited_refs:
            if "password=" in ref.lower() or "api_key=" in ref.lower():
                raise LifecycleValidationError("mor.validation.secret", "secrets forbidden in inherited refs")
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "mor-successor-seed",
            "schema_version": MOR_SCHEMA_VERSION,
            "successor_seed_id": self.successor_seed_id,
            "death_notice_ref": self.death_notice_ref,
            "seed_type": self.seed_type,
            "inherited_refs": list(self.inherited_refs),
            "forbidden_inheritance": list(self.forbidden_inheritance),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise LifecycleValidationError("mor.validation.secret", "secrets forbidden in mortality records")


def death_notice_from_fixture(fixture: dict[str, str]) -> AgentDeathNotice:
    return AgentDeathNotice(
        death_notice_id=fixture["death_notice_id"],
        agent_id=fixture.get("agent_id", "agent0"),
        termination_mode=fixture.get("termination_mode", "graceful_complete"),  # type: ignore[arg-type]
        termination_reason=fixture.get("termination_reason", "fixture termination"),
        event_head=fixture.get("event_head", "sha256:event-head-fixture"),
        world_state_hash=fixture.get("world_state_hash", "sha256:world-fixture"),
        created_at=fixture.get("created_at", "2026-06-12T22:00:00.000000Z"),
        expiry=fixture.get("expiry", "2026-06-13T22:00:00.000000Z"),
    )


def final_message_from_fixture(fixture: dict[str, str]) -> FinalMessage:
    return FinalMessage(
        final_message_id=fixture["final_message_id"],
        agent_id=fixture.get("agent_id", "agent0"),
        message_type=fixture.get("message_type", "completion_summary"),
        summary=fixture.get("summary", "fixture summary"),
    )


def successor_seed_from_fixture(fixture: dict[str, str]) -> SuccessorSeed:
    forbidden = tuple(
        item.strip()
        for item in fixture.get("forbidden_inheritance", "authority,identity_continuity").split(",")
        if item.strip()
    )
    inherited = tuple(
        item.strip() for item in fixture.get("inherited_refs", "mem:fixture-ref").split(",") if item.strip()
    )
    return SuccessorSeed(
        successor_seed_id=fixture["successor_seed_id"],
        death_notice_ref=fixture.get("death_notice_ref", "mor:death-fixture"),
        seed_type=fixture.get("seed_type", "archive_only"),
        inherited_refs=inherited,
        forbidden_inheritance=forbidden,  # type: ignore[arg-type]
    )


__all__ = [
    "MOR_SCHEMA_VERSION",
    "AgentDeathNotice",
    "FinalMessage",
    "MemoryOffering",
    "SuccessorSeed",
    "death_notice_from_fixture",
    "final_message_from_fixture",
    "successor_seed_from_fixture",
]
