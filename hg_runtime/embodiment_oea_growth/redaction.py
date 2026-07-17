"""Embodiment growth secret redaction — display safety."""

from __future__ import annotations

import re

_SECRET_PATTERNS = (
    re.compile(r"api_key=\S+", re.IGNORECASE),
    re.compile(r"password=\S+", re.IGNORECASE),
    re.compile(r"bearer\s+\S+", re.IGNORECASE),
)


def redact_growth_text(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


__all__ = ["redact_growth_text"]
