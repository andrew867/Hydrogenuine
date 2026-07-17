"""P26 artifact redaction checks."""

from __future__ import annotations

import re
from typing import Any

SECRET_RE = re.compile(r"(api[_-]?key|secret|token|password|bearer|sk-[A-Za-z0-9])", re.IGNORECASE)


def secret_scan(value: Any) -> bool:
    if isinstance(value, str):
        return SECRET_RE.search(value) is None
    if isinstance(value, dict):
        return all(secret_scan(v) for v in value.values())
    if isinstance(value, list | tuple | set):
        return all(secret_scan(v) for v in value)
    return True
