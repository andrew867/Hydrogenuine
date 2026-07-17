"""WILL receipts, traces, and events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from hg_runtime.will_module.hash import will_hash
from hg_runtime.will_module.schema import FIXTURE_CLOCK, ConsentPosture, VetoState, WillDecisionEffect, WillSource

WILL_EVENT_TYPES = (
    "WILL_PROFILE_LOADED",
    "WILL_ENVELOPE_CREATED",
    "WILL_CONTEXT_ATTACHED",
    "WILL_REAFFIRMATION_REQUIRED",
    "WILL_REAFFIRMED",
    "WILL_EXPIRED",
    "WILL_VETO_SET",
    "WILL_VETO_HARD_STOP",
    "WILL_CONFLICT_DETECTED",
    "WILL_TOOL_REQUEST_CONTEXT_ATTACHED",
    "WILL_MEMORY_REQUEST_CONTEXT_ATTACHED",
    "WILL_AUTHORITY_CONVERSION_REJECTED",
)


@dataclass
class WillReceipt:
    receipt_id: str
    run_id: str
    will_id: str
    event_type: str
    source: WillSource
    summary: str
    effect: WillDecisionEffect
    veto_state: VetoState
    consent_posture: ConsentPosture
    expires_at: str
    timestamp: str = FIXTURE_CLOCK
    previous_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "will-receipt",
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "will_id": self.will_id,
            "event_type": self.event_type,
            "source": self.source.value,
            "summary": self.summary,
            "effect": self.effect.value,
            "veto_state": self.veto_state.value,
            "consent_posture": self.consent_posture.value,
            "expires_at": self.expires_at,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["hash"] = will_hash(payload)
        return payload


@dataclass
class WillTrace:
    run_id: str
    will_id: str
    events: list[dict[str, Any]] = field(default_factory=list)

    def append(self, event_type: str, **detail: Any) -> dict[str, Any]:
        event = {
            "schema": "will-trace-event",
            "event_type": event_type,
            "run_id": self.run_id,
            "will_id": self.will_id,
            "detail": detail,
            "timestamp": FIXTURE_CLOCK,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        event["event_hash"] = will_hash(event)
        self.events.append(event)
        return event


@dataclass
class WillConflict:
    will_id: str
    conflict_type: str
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "will-conflict",
            "will_id": self.will_id,
            "conflict_type": self.conflict_type,
            "detail": self.detail,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class WillDecay:
    will_id: str
    reason: str

    def to_payload(self) -> dict[str, Any]:
        return {"schema": "will-decay", "will_id": self.will_id, "reason": self.reason}


@dataclass
class WillReaffirmation:
    will_id: str
    operator_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "will-reaffirmation",
            "will_id": self.will_id,
            "operator_ref": self.operator_ref,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def create_envelope_receipt(envelope_payload: dict[str, Any], *, event_type: str = "WILL_ENVELOPE_CREATED") -> WillReceipt:
    return WillReceipt(
        receipt_id=f"willrcpt-{uuid.uuid4().hex[:12]}",
        run_id=envelope_payload["run_id"],
        will_id=envelope_payload["will_id"],
        event_type=event_type,
        source=WillSource(envelope_payload["source"]),
        summary=envelope_payload.get("intent_summary", ""),
        effect=WillDecisionEffect.NO_EFFECT,
        veto_state=VetoState(envelope_payload.get("veto_state", "NONE")),
        consent_posture=ConsentPosture(envelope_payload.get("consent_posture", "ASK_FIRST")),
        expires_at=envelope_payload.get("expires_at", FIXTURE_CLOCK),
    )


__all__ = [
    "WILL_EVENT_TYPES",
    "WillConflict",
    "WillDecay",
    "WillReceipt",
    "WillReaffirmation",
    "WillTrace",
    "create_envelope_receipt",
]
