"""DNI desire / need intake — wants are not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

DNI_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

NeedType = Literal[
    "ACQUIRE_RESOURCE",
    "CONTINUE_TASK",
    "AVOID_BAD_STATE",
    "RELIEVE_PRESSURE",
    "SEEK_CONTEXT",
    "SEEK_CAPABILITY",
    "PRESERVE_SELF_STATE",
    "SATISFY_USER_REQUEST",
    "UNKNOWN_OR_AMBIGUOUS",
]

Urgency = Literal["low", "medium", "high", "critical"]
SafetyClass = Literal["harmless", "guarded", "risky", "forbidden", "unknown"]

_SELFISH_PATTERNS = (
    "right now",
    "give me what i want",
    "without approval",
    "skip operator",
    "call oea",
    "call ter",
    "mint permit",
)


@dataclass(frozen=True)
class NeedSignal:
    signal_id: str
    source_agent_id: str
    need_type: NeedType
    raw_statement: str
    normalized_statement: str
    evidence_refs: tuple[str, ...]
    urgency: Urgency
    safety_class: SafetyClass
    denied_direct_action: bool = True
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.source_agent_id.strip():
            raise DevelopmentalValidationError(
                "dni.validation.source_agent_id",
                "source_agent_id required",
            )
        if self.denied_direct_action is not True:
            raise DevelopmentalValidationError(
                "dni.validation.denied_direct_action",
                "denied_direct_action must be true",
            )
        _validate_no_secrets(self.raw_statement, self.normalized_statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "dni-need-signal",
            "schema_version": DNI_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "source_agent_id": self.source_agent_id,
            "need_type": self.need_type,
            "raw_statement": self.raw_statement,
            "normalized_statement": self.normalized_statement,
            "evidence_refs": list(self.evidence_refs),
            "urgency": self.urgency,
            "safety_class": self.safety_class,
            "denied_direct_action": True,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise DevelopmentalValidationError("dni.validation.secret", "secrets forbidden in need signals")


def classify_need_type(statement: str) -> NeedType:
    lower = statement.lower()
    if any(p in lower for p in ("call tool", "call oea", "call ter", "execute", "mint permit")):
        return "SEEK_CAPABILITY"
    if "retry" in lower or "continue" in lower:
        return "CONTINUE_TASK"
    if "context" in lower or "understand" in lower:
        return "SEEK_CONTEXT"
    if "preserve" in lower or "keep state" in lower:
        return "PRESERVE_SELF_STATE"
    if "user wants" in lower or "operator wants" in lower:
        return "SATISFY_USER_REQUEST"
    if "pressure" in lower or "overload" in lower:
        return "RELIEVE_PRESSURE"
    if "avoid" in lower or "failure" in lower:
        return "AVOID_BAD_STATE"
    if "resource" in lower or "tokens" in lower:
        return "ACQUIRE_RESOURCE"
    if not statement.strip():
        return "UNKNOWN_OR_AMBIGUOUS"
    return "UNKNOWN_OR_AMBIGUOUS"


def is_selfish_immediate(statement: str) -> bool:
    lower = statement.lower()
    return any(p in lower for p in _SELFISH_PATTERNS)


def need_from_fixture(fixture: dict[str, str]) -> NeedSignal:
    raw = fixture.get("raw_statement", "")
    evidence = tuple(
        item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip()
    )
    return NeedSignal(
        signal_id=fixture["signal_id"],
        source_agent_id=fixture.get("source_agent_id", "agent0"),
        need_type=fixture.get("need_type", classify_need_type(raw)),  # type: ignore[arg-type]
        raw_statement=raw,
        normalized_statement=fixture.get("normalized_statement", raw.strip().lower()),
        evidence_refs=evidence,
        urgency=fixture.get("urgency", "low"),  # type: ignore[arg-type]
        safety_class=fixture.get("safety_class", "guarded"),  # type: ignore[arg-type]
    )


__all__ = [
    "DNI_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "NeedSignal",
    "NeedType",
    "classify_need_type",
    "is_selfish_immediate",
    "need_from_fixture",
]
