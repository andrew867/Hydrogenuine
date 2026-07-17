"""UEAK execution request/result models — Phase 1 commit scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Mapping, Tuple

ExecutionStatus = Literal["COMMITTED", "DENIED", "FAILED"]


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    proposed_action: Mapping[str, Any]
    required_capability: str
    effect_class: str
    governance_trace_refs: Tuple[str, ...] = ()
    permit_ref: str | None = None
    decision_id: str | None = None
    decision_event_id: str | None = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "proposed_action": dict(self.proposed_action),
            "required_capability": self.required_capability,
            "effect_class": self.effect_class,
            "governance_trace_refs": list(self.governance_trace_refs),
            "permit_ref": self.permit_ref,
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    reason_code: str
    request_id: str
    event_refs: Tuple[str, ...] = ()
    commit_ref: str | None = None
    capability_id: str | None = None
    effect_class: str | None = None

    def to_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "status": self.status,
            "reason_code": self.reason_code,
            "request_id": self.request_id,
            "event_refs": list(self.event_refs),
        }
        if self.commit_ref is not None:
            payload["commit_ref"] = self.commit_ref
        if self.capability_id is not None:
            payload["capability_id"] = self.capability_id
        if self.effect_class is not None:
            payload["effect_class"] = self.effect_class
        return payload


__all__ = ["ExecutionRequest", "ExecutionResult", "ExecutionStatus"]
