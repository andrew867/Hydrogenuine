"""Redaction guards — reject secrets and hidden chain-of-thought."""

from __future__ import annotations

import re
from typing import Any, Mapping

from hg_runtime.agent_zero_state.types import HIDDEN_COT_FIELDS

SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.I),
    re.compile(r"token\s*[:=]\s*\S+", re.I),
    re.compile(r"password\s*[:=]\s*\S+", re.I),
    re.compile(r"secret\s*[:=]\s*\S+", re.I),
]

SECRET_FIELD_NAMES = frozenset({
    "token",
    "api_key",
    "password",
    "secret",
    "bearer",
    "credential_value",
    "hg_moltbook_token",
    "hg_fourclaw_token",
})


def contains_hidden_cot(payload: Mapping[str, Any] | Any) -> bool:
    """Detect hidden chain-of-thought field names in nested dicts."""
    if isinstance(payload, Mapping):
        for key, val in payload.items():
            if str(key).lower() in HIDDEN_COT_FIELDS:
                return True
            if contains_hidden_cot(val):
                return True
    elif isinstance(payload, list):
        return any(contains_hidden_cot(item) for item in payload)
    return False


def contains_secret(payload: Mapping[str, Any] | Any) -> bool:
    """Detect obvious secrets in field names or string values."""
    if isinstance(payload, Mapping):
        for key, val in payload.items():
            if str(key).lower() in SECRET_FIELD_NAMES:
                return True
            if contains_secret(val):
                return True
    elif isinstance(payload, list):
        return any(contains_secret(item) for item in payload)
    elif isinstance(payload, str):
        text = payload.strip()
        if not text:
            return False
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                return True
    return False


def scan_payload(payload: Mapping[str, Any]) -> tuple[bool, bool]:
    """Return (has_secret, has_hidden_cot)."""
    return contains_secret(payload), contains_hidden_cot(payload)


__all__ = [
    "SECRET_FIELD_NAMES",
    "contains_hidden_cot",
    "contains_secret",
    "scan_payload",
]
