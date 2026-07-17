"""Redact environment values for doctor output (CT-16 ENV)."""

from __future__ import annotations

import os
from typing import Any

from hg_core.secrets.redact import redact_text

_REDACTED = "[REDACTED]"

_SENSITIVE_FRAGMENTS = (
    "key",
    "secret",
    "token",
    "password",
    "credential",
    "authorization",
    "api_key",
)


def _is_sensitive_name(name: str) -> bool:
    lowered = name.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS)


def redact_env_value(name: str, value: str) -> str:
    if not value:
        return ""
    if _is_sensitive_name(name):
        return _REDACTED
    redacted, _ = redact_text(value)
    return redacted


def snapshot_env(names: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        raw = os.environ.get(name, "")
        out[name] = redact_env_value(name, raw) if raw else ""
    return out


def redact_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Deep-redact string leaves in a doctor report."""

    def _walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: _walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [_walk(item) for item in value]
        if isinstance(value, str):
            text, _ = redact_text(value)
            return text
        return value

    return _walk(payload)


__all__ = ["redact_env_value", "redact_report", "snapshot_env"]
