"""Cloud browser governance shared types."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

FIXTURE_CLOCK = "2026-06-15T02:00:00.000000Z"

DecisionClass = Literal["AUTO_APPROVE", "AUTO_WARN", "FULL_STOP", "OPERATOR_REVIEW", "PERMIT_REQUIRED", "DENIED"]

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|bearer)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
)


def advisory_envelope(**extra: Any) -> dict[str, Any]:
    base = {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "is_permit": False,
        "live_side_effect": False,
    }
    base.update(extra)
    if base.get("permission_granted") or base.get("authority_created"):
        raise ValueError("cloud browser governance must not grant permission")
    return base


def stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def redact_secrets(text: str) -> str:
    out = text
    for pat in SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


__all__ = ["DecisionClass", "FIXTURE_CLOCK", "SECRET_PATTERNS", "advisory_envelope", "redact_secrets", "stable_hash"]
