"""RTC memory contract types — context only, no authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MemoryStatus = Literal["ok", "noop", "failed"]

MEMORY_SCHEMA = "rtc-memory"
MEMORY_SCHEMA_VERSION = "1.0"

SECRET_KEY_FRAGMENTS = ("api_key", "apikey", "token", "secret", "password", "credential")


@dataclass(frozen=True)
class MemoryReference:
    """Stable reference to a stored memory artifact."""

    memory_ref: str
    store: str
    event_refs: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "memory_ref": self.memory_ref,
            "store": self.store,
            "event_refs": list(self.event_refs),
        }


@dataclass(frozen=True)
class MemoryRetrieveRequest:
    runtime_id: str
    session_id: str | None
    event_refs: tuple[str, ...]
    max_tokens: int = 1500

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": MEMORY_SCHEMA,
            "schema_version": MEMORY_SCHEMA_VERSION,
            "kind": "retrieve_request",
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "event_refs": list(self.event_refs),
            "max_tokens": self.max_tokens,
        }


@dataclass(frozen=True)
class MemoryRetrieveResult:
    status: MemoryStatus
    context: dict[str, Any]
    provenance: dict[str, Any]
    reason_code: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": MEMORY_SCHEMA,
            "schema_version": MEMORY_SCHEMA_VERSION,
            "kind": "retrieve_result",
            "status": self.status,
            "context": redact_mapping(self.context),
            "provenance": self.provenance,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class MemoryStoreRequest:
    runtime_id: str
    session_id: str | None
    event_refs: tuple[str, ...]
    proposal_refs: tuple[str, ...]
    result_refs: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": MEMORY_SCHEMA,
            "schema_version": MEMORY_SCHEMA_VERSION,
            "kind": "store_request",
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "event_refs": list(self.event_refs),
            "proposal_refs": list(self.proposal_refs),
            "result_refs": list(self.result_refs),
        }


@dataclass(frozen=True)
class MemoryStoreResult:
    status: MemoryStatus
    reference: MemoryReference | None
    reason_code: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": MEMORY_SCHEMA,
            "schema_version": MEMORY_SCHEMA_VERSION,
            "kind": "store_result",
            "status": self.status,
            "reason_code": self.reason_code,
        }
        if self.reference is not None:
            payload.update(self.reference.to_payload())
        return payload


def redact_mapping(value: Any) -> Any:
    """Remove obvious secret fields from memory context payloads."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(fragment in key_lower for fragment in SECRET_KEY_FRAGMENTS):
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_mapping(item)
        return out
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    return value


__all__ = [
    "MEMORY_SCHEMA",
    "MEMORY_SCHEMA_VERSION",
    "MemoryReference",
    "MemoryRetrieveRequest",
    "MemoryRetrieveResult",
    "MemoryStatus",
    "MemoryStoreRequest",
    "MemoryStoreResult",
    "redact_mapping",
]
