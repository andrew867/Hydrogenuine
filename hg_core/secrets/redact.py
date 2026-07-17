"""Central secret redaction — events, receipts, TER, PLT, bundles (CT-02)."""

from __future__ import annotations

import json
import re
from typing import Any

from hg_core.secrets.canary import contains_canary
from hg_core.security.redaction import SENSITIVE_KEYS, redact_json, redact_text as _base_redact_text

_REDACTED = "[REDACTED]"

_EXTRA_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)AWS_SECRET_ACCESS_KEY=\S+"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
)

_SENSITIVE_KEY_FRAGMENTS = ("secret", "token", "password", "credential", "api_key", "apikey", "authorization")


class SecretLeakError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class RedactionFailure(SecretLeakError):
    """Permanent failure — refuse rather than emit unredacted material."""


def redact_text(text: str) -> tuple[str, bool]:
    if not text:
        return text, False
    applied = False
    out = _base_redact_text(text)
    if out != text:
        applied = True
    for pattern in _EXTRA_PATTERNS:
        new_text, count = pattern.subn(_REDACTED, out)
        if count:
            applied = True
            out = new_text
    for marker in _all_canary_markers():
        if marker in out:
            out = out.replace(marker, _REDACTED)
            applied = True
    return out, applied


def redact_payload(payload: Any) -> Any:
    redacted = redact_json(payload, sensitive_keys=SENSITIVE_KEYS)
    if isinstance(redacted, dict):
        return _deep_redact_dict(redacted)
    if isinstance(redacted, str):
        text, _ = redact_text(redacted)
        return text
    return redacted


def _deep_redact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in payload.items():
        key_lower = key.lower()
        if any(fragment in key_lower for fragment in _SENSITIVE_KEY_FRAGMENTS):
            result[key] = _REDACTED
            continue
        if isinstance(value, str):
            text, _ = redact_text(value)
            result[key] = text
        elif isinstance(value, dict):
            result[key] = _deep_redact_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _deep_redact_dict(item) if isinstance(item, dict) else (
                    redact_text(item)[0] if isinstance(item, str) else item
                )
                for item in value
            ]
        else:
            result[key] = value
    return result


def contains_raw_secret_pattern(text: str) -> bool:
    if not text or text == _REDACTED:
        return False
    if contains_canary(text):
        return True
    for pattern in _EXTRA_PATTERNS:
        if pattern.search(text):
            return True
    return False


def contains_leak(payload: Any) -> bool:
    serialized = json.dumps(payload, default=str, sort_keys=True)
    if contains_canary(serialized):
        return True
    return contains_raw_secret_pattern(serialized)


def refuse_if_leak(payload: Any, *, context: str = "payload") -> None:
    if contains_leak(payload):
        raise RedactionFailure(f"secret_leak_detected:{context}")


def redact_or_refuse(payload: Any, *, context: str = "payload") -> Any:
    redacted = redact_payload(payload)
    refuse_if_leak(redacted, context=context)
    return redacted


def _all_canary_markers() -> frozenset[str]:
    from hg_core.secrets.canary import all_canary_values

    return all_canary_values()


__all__ = [
    "RedactionFailure",
    "SecretLeakError",
    "contains_leak",
    "contains_raw_secret_pattern",
    "redact_or_refuse",
    "redact_payload",
    "redact_text",
    "refuse_if_leak",
]
