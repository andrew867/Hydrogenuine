"""Redaction checks for ORP proof artifacts."""

from __future__ import annotations

import re
from typing import Any

SECRET_RE = re.compile(r"(api[_-]?key|password|bearer\s+|sk-[A-Za-z0-9]{8,})", re.IGNORECASE)
SAFE_KEYS = {
    "secret_redaction_passed",
    "secrets_emitted",
    "no_secrets_in_receipts",
}


def secret_scan(value: Any) -> bool:
    if isinstance(value, dict):
        return all((key in SAFE_KEYS or not SECRET_RE.search(str(key))) and secret_scan(item) for key, item in value.items())
    if isinstance(value, list):
        return all(secret_scan(item) for item in value)
    if isinstance(value, str):
        return not SECRET_RE.search(value)
    return True
