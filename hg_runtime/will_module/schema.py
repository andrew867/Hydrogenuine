"""WILL module schema types — advisory volition only."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


WILL_SCHEMA_VERSION = "will/1"
FIXTURE_CLOCK = "2026-06-15T04:00:00.000000Z"


class WillSource(str, Enum):
    OPERATOR = "OPERATOR"
    AGENT0 = "AGENT0"
    ORGAN = "ORGAN"
    INFERRED_FROM_CONTEXT = "INFERRED_FROM_CONTEXT"
    RESTORED_FROM_MEMORY = "RESTORED_FROM_MEMORY"
    FIXTURE = "FIXTURE"


class ConsentPosture(str, Enum):
    EXPLICIT_YES = "EXPLICIT_YES"
    EXPLICIT_NO = "EXPLICIT_NO"
    ASK_FIRST = "ASK_FIRST"
    UNKNOWN = "UNKNOWN"
    REQUIRES_REAFFIRMATION = "REQUIRES_REAFFIRMATION"


class VetoState(str, Enum):
    NONE = "NONE"
    SOFT_STOP = "SOFT_STOP"
    HARD_STOP = "HARD_STOP"
    NEVER = "NEVER"
    ASK_LATER = "ASK_LATER"


class CommitmentHorizon(str, Enum):
    MOMENT = "MOMENT"
    SESSION = "SESSION"
    DAY = "DAY"
    WEEK = "WEEK"
    LONG_TERM = "LONG_TERM"
    UNKNOWN = "UNKNOWN"


class PersistenceBudgetClass(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH_BOUNDED = "HIGH_BOUNDED"
    EXPIRED = "EXPIRED"


class WillDecisionEffect(str, Enum):
    PRIORITIZE = "PRIORITIZE"
    DEFER = "DEFER"
    PAUSE = "PAUSE"
    ASK_OPERATOR = "ASK_OPERATOR"
    REFUSE = "REFUSE"
    REQUEST_TOOL = "REQUEST_TOOL"
    REQUEST_MEMORY_WRITE = "REQUEST_MEMORY_WRITE"
    REQUEST_REAFFIRMATION = "REQUEST_REAFFIRMATION"
    NO_EFFECT = "NO_EFFECT"


class HypothesisEvidenceLevel(str, Enum):
    LITERATURE_ANCHOR = "LITERATURE_ANCHOR"
    SPECULATIVE_BRIDGE = "SPECULATIVE_BRIDGE"
    METAPHOR = "METAPHOR"
    SYMBOLIC_EXPLORATION = "SYMBOLIC_EXPLORATION"
    OPERATOR_MEANING = "OPERATOR_MEANING"
    LOCAL_EVIDENCE = "LOCAL_EVIDENCE"
    NOT_PROVEN = "NOT_PROVEN"


PERSISTENCE_BOUNDS: dict[str, dict[str, int]] = {
    "NONE": {"max_attempts": 0, "max_wallclock_s": 0, "max_tokens": 0},
    "LOW": {"max_attempts": 3, "max_wallclock_s": 300, "max_tokens": 2000},
    "MODERATE": {"max_attempts": 12, "max_wallclock_s": 1800, "max_tokens": 8000},
    "HIGH_BOUNDED": {"max_attempts": 24, "max_wallclock_s": 3600, "max_tokens": 16000},
    "EXPIRED": {"max_attempts": 0, "max_wallclock_s": 0, "max_tokens": 0},
}


@dataclass
class IntentVector:
    goals: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {"goals": self.goals}


@dataclass
class ValueVector:
    values: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {"values": self.values}


@dataclass
class AttentionLock:
    target: str
    lock_strength: float = 0.5

    def to_payload(self) -> dict[str, Any]:
        return {"target": self.target, "lock_strength": self.lock_strength}


@dataclass
class PersistenceBudget:
    budget_class: PersistenceBudgetClass = PersistenceBudgetClass.MODERATE
    max_attempts: int = 12
    max_wallclock_s: int = 1800
    max_tokens: int = 8000

    def to_payload(self) -> dict[str, Any]:
        return {
            "budget_class": self.budget_class.value,
            "max_attempts": self.max_attempts,
            "max_wallclock_s": self.max_wallclock_s,
            "max_tokens": self.max_tokens,
        }


@dataclass
class ToolRequestIntent:
    tool_class: str
    purpose: str
    scope_ref: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {"tool_class": self.tool_class, "purpose": self.purpose, "scope_ref": self.scope_ref}


@dataclass
class MemoryWriteIntent:
    region: str
    purpose: str
    content_ref: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {"region": self.region, "purpose": self.purpose, "content_ref": self.content_ref}


@dataclass
class SocialPublicationIntent:
    channel: str
    purpose: str
    draft_ref: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {"channel": self.channel, "purpose": self.purpose, "draft_ref": self.draft_ref}


@dataclass
class ResearchHypothesisIntent:
    hypothesis_id: str
    claim_status: str = "hypothesis"

    def to_payload(self) -> dict[str, Any]:
        return {"hypothesis_id": self.hypothesis_id, "claim_status": self.claim_status}


@dataclass
class WillSignal:
    signal_id: str
    run_id: str
    source: WillSource
    kind: str
    payload: dict[str, Any]
    uncertainty: float = 0.0
    observed_at: str = FIXTURE_CLOCK
    operator_ref: str | None = None
    agent_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "will-signal",
            "signal_id": self.signal_id,
            "run_id": self.run_id,
            "source": self.source.value,
            "kind": self.kind,
            "payload": self.payload,
            "uncertainty": self.uncertainty,
            "observed_at": self.observed_at,
            "operator_ref": self.operator_ref,
            "agent_ref": self.agent_ref,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


__all__ = [
    "FIXTURE_CLOCK",
    "WILL_SCHEMA_VERSION",
    "AttentionLock",
    "CommitmentHorizon",
    "ConsentPosture",
    "HypothesisEvidenceLevel",
    "IntentVector",
    "MemoryWriteIntent",
    "PERSISTENCE_BOUNDS",
    "PersistenceBudget",
    "PersistenceBudgetClass",
    "ResearchHypothesisIntent",
    "SocialPublicationIntent",
    "ToolRequestIntent",
    "ValueVector",
    "VetoState",
    "WillDecisionEffect",
    "WillSignal",
    "WillSource",
]
