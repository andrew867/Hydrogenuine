"""Operator surface secret redaction — display safety."""

from __future__ import annotations

import re

_SECRET_PATTERNS = (
    re.compile(r"api_key=\S+", re.IGNORECASE),
    re.compile(r"password=\S+", re.IGNORECASE),
    re.compile(r"bearer\s+\S+", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
)


def redact_surface_text(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def contains_secret_material(text: str) -> bool:
    return redact_surface_text(text) != text


__all__ = ["contains_secret_material", "redact_surface_text"]
