"""Serialization helpers for the EXCITON action model."""

from __future__ import annotations

import json
from typing import Any

from hg_runtime.exciton_action_model.schema import (
    AgentActionDecision,
    AgentActionReceipt,
    AgentActionRequest,
)


def request_to_json(request: AgentActionRequest, *, indent: int | None = None) -> str:
    return json.dumps(request.to_payload(), indent=indent, sort_keys=True)


def request_from_json(text: str) -> AgentActionRequest:
    return AgentActionRequest.from_payload(json.loads(text))


def decision_to_json(decision: AgentActionDecision, *, indent: int | None = None) -> str:
    return json.dumps(decision.to_payload(), indent=indent, sort_keys=True)


def decision_from_json(text: str) -> AgentActionDecision:
    return AgentActionDecision.from_payload(json.loads(text))


def receipt_to_json(receipt: AgentActionReceipt, *, indent: int | None = None) -> str:
    return json.dumps(receipt.to_payload(), indent=indent, sort_keys=True)


def receipt_from_json(text: str) -> AgentActionReceipt:
    return AgentActionReceipt.from_payload(json.loads(text))


def roundtrip_request(request: AgentActionRequest) -> AgentActionRequest:
    return AgentActionRequest.from_payload(request.to_payload())


def roundtrip_decision(decision: AgentActionDecision) -> AgentActionDecision:
    return AgentActionDecision.from_payload(decision.to_payload())


def roundtrip_receipt(receipt: AgentActionReceipt) -> AgentActionReceipt:
    return AgentActionReceipt.from_payload(receipt.to_payload())


def payload_frozen_constants(payload: dict[str, Any]) -> dict[str, bool]:
    return {
        "advisory_only": bool(payload.get("advisory_only")),
        "permission_granted": bool(payload.get("permission_granted")),
        "authority_created": bool(payload.get("authority_created")),
    }


__all__ = [
    "decision_from_json",
    "decision_to_json",
    "payload_frozen_constants",
    "receipt_from_json",
    "receipt_to_json",
    "request_from_json",
    "request_to_json",
    "roundtrip_decision",
    "roundtrip_receipt",
    "roundtrip_request",
]
