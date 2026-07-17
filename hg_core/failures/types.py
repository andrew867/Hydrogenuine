"""CT-05 failure taxonomy types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReasonCodeRecord:
    code: str
    state: str
    subsystem: str
    retryable: bool
    display_label: str
    legacy_aliases: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "state": self.state,
            "subsystem": self.subsystem,
            "retryable": self.retryable,
            "display_label": self.display_label,
            "legacy_aliases": list(self.legacy_aliases),
        }


@dataclass(frozen=True)
class TerminalOutcome:
    state: str
    reason_code: str
    retryable: bool
    incident_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "state": self.state,
            "reason_code": self.reason_code,
            "retryable": self.retryable,
        }
        if self.incident_ref:
            payload["incident_ref"] = self.incident_ref
        return payload


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str
    canonical_code: str | None = None
    record: ReasonCodeRecord | None = None


__all__ = ["ReasonCodeRecord", "TerminalOutcome", "ValidationResult"]
