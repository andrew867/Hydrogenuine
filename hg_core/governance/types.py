"""GPP permit binding types — Phase 1 enforcement scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from hg_core.governance.canonical_hash import canonical_hash, without_keys

PERMIT_SCHEMA = "gpp-permit"
PERMIT_SCHEMA_VERSION = "1.0"
DENY_SCHEMA = "gpp-bind-deny"
DENY_SCHEMA_VERSION = "1.0"


class BindValidationError(ValueError):
    """Bind request or descriptor failed structural validation."""


@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    effect_class: str
    description: str = ""
    bind_allowed: bool = True


@dataclass(frozen=True)
class DecisionReference:
    """Explicit decision provenance fixture until SOAR/HAL integration lands."""

    decision_ref: str
    verdict: str
    reason_code: Optional[str] = None


@dataclass(frozen=True)
class TraceRef:
    trace_path: str
    trace_seq: int
    trace_event_hash: str


@dataclass(frozen=True)
class BindRequest:
    request_id: str
    capability_id: str
    effect_class: str
    decision_ref: str


@dataclass(frozen=True)
class Permit:
    permit_id: str
    request_id: str
    capability_id: str
    effect_class: str
    issued_at: str
    expires_at: Optional[str]
    decision_ref: str
    trace_ref: TraceRef
    permit_hash: str = field(init=False)

    def __post_init__(self) -> None:
        body = self.to_payload(include_hash=False)
        object.__setattr__(self, "permit_hash", canonical_hash(body))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": PERMIT_SCHEMA,
            "schema_version": PERMIT_SCHEMA_VERSION,
            "permit_id": self.permit_id,
            "request_id": self.request_id,
            "capability_id": self.capability_id,
            "effect_class": self.effect_class,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "decision_ref": self.decision_ref,
            "trace_ref": {
                "trace_path": self.trace_ref.trace_path,
                "trace_seq": self.trace_ref.trace_seq,
                "trace_event_hash": self.trace_ref.trace_event_hash,
            },
        }
        if include_hash:
            payload["permit_hash"] = self.permit_hash
        return payload


@dataclass(frozen=True)
class DenyRecord:
    request_id: str
    capability_id: str
    effect_class: str
    reason_code: str
    decision_ref: str
    denied_at: str
    trace_ref: Optional[TraceRef] = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": DENY_SCHEMA,
            "schema_version": DENY_SCHEMA_VERSION,
            "request_id": self.request_id,
            "capability_id": self.capability_id,
            "effect_class": self.effect_class,
            "reason_code": self.reason_code,
            "decision_ref": self.decision_ref,
            "denied_at": self.denied_at,
        }
        if self.trace_ref is not None:
            payload["trace_ref"] = {
                "trace_path": self.trace_ref.trace_path,
                "trace_seq": self.trace_ref.trace_seq,
                "trace_event_hash": self.trace_ref.trace_event_hash,
            }
        return payload


@dataclass(frozen=True)
class BindResult:
    outcome: str
    permit: Optional[Permit] = None
    deny: Optional[DenyRecord] = None
    trace_record: Optional[Mapping[str, Any]] = None


def permit_body_hash(payload: Mapping[str, Any]) -> str:
    """Deterministic permit hash excluding the stored hash field."""
    return canonical_hash(without_keys(payload, {"permit_hash"}))


__all__ = [
    "BindRequest",
    "BindResult",
    "BindValidationError",
    "CapabilityDescriptor",
    "DecisionReference",
    "DenyRecord",
    "PERMIT_SCHEMA",
    "PERMIT_SCHEMA_VERSION",
    "Permit",
    "TraceRef",
    "permit_body_hash",
]
