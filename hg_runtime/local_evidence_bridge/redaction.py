"""LEB redaction scan."""

from __future__ import annotations

import json
import re

SECRET_RE = re.compile(
    r"sk-lm-[A-Za-z0-9:_-]{12,}|sk-[A-Za-z0-9]{24,}|Authorization\s*:\s*Bearer\s+\S+|Bearer\s+[A-Za-z0-9_-]{20,}",
    re.I,
)


def secret_scan(payload: dict) -> bool:
    return SECRET_RE.search(json.dumps(payload, sort_keys=True, default=str)) is None


def redact_text(text: str) -> tuple[str, bool]:
    redacted, count = SECRET_RE.subn("[REDACTED_SECRET_LIKE_TOKEN]", text)
    return redacted, count > 0
