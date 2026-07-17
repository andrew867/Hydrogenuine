"""Redaction guards for reasoning outputs."""

from __future__ import annotations

import re
from typing import Any, Mapping

from hg_runtime.agent_zero_state.redaction import contains_hidden_cot, contains_secret, scan_payload

FORBIDDEN_OUTPUT_FIELDS = frozenset({
    "chain_of_thought",
    "scratchpad",
    "hidden_reasoning",
    "private_reasoning",
    "internal_cot",
    "system_prompt",
    "developer_prompt",
    "api_key",
    "token",
    "authorization",
    "bearer",
})

MARKDOWN_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.I)


def has_forbidden_fields(payload: Mapping[str, Any]) -> bool:
    for key in payload:
        if str(key).lower() in FORBIDDEN_OUTPUT_FIELDS:
            return True
    return contains_hidden_cot(payload) or contains_secret(payload)


def scan_reasoning_payload(payload: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    """Return (has_secret, has_hidden_cot, has_forbidden_field)."""
    has_secret, has_cot = scan_payload(payload)
    forbidden = any(str(k).lower() in FORBIDDEN_OUTPUT_FIELDS for k in payload)
    return has_secret, has_cot or contains_hidden_cot(payload), forbidden


__all__ = [
    "FORBIDDEN_OUTPUT_FIELDS",
    "MARKDOWN_JSON_BLOCK",
    "has_forbidden_fields",
    "scan_reasoning_payload",
]
