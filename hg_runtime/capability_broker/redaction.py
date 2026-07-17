"""Redaction guards for broker decisions and audit records."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.agent_zero_state.redaction import contains_hidden_cot, contains_secret, scan_payload

FORBIDDEN_AUDIT_FIELDS = frozenset({
    "chain_of_thought",
    "scratchpad",
    "hidden_reasoning",
    "private_reasoning",
    "internal_cot",
    "system_prompt",
    "developer_prompt",
    "raw_model_output",
    "api_key",
    "token",
    "authorization",
    "bearer",
})


def has_forbidden_audit_field(payload: Mapping[str, Any]) -> bool:
    for key in payload:
        if str(key).lower() in FORBIDDEN_AUDIT_FIELDS:
            return True
    if contains_hidden_cot(payload) or contains_secret(payload):
        return True
    reasons = payload.get("refusal_reasons")
    if isinstance(reasons, list):
        for item in reasons:
            if isinstance(item, str) and "scratchpad" in item.lower():
                return True
    return False


def scan_broker_payload(payload: Mapping[str, Any]) -> tuple[bool, bool]:
    return scan_payload(payload)


__all__ = [
    "FORBIDDEN_AUDIT_FIELDS",
    "has_forbidden_audit_field",
    "scan_broker_payload",
]
