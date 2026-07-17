"""Redaction helpers for P27 batch skill graph."""

from __future__ import annotations

import json
import re
from typing import Any

SECRET_RE = re.compile(r"(api[_-]?key|password|bearer\s+[a-z0-9._-]+|sk-[a-zA-Z0-9])", re.IGNORECASE)


def secret_scan(payload: Any) -> bool:
    text = json.dumps(payload, sort_keys=True, default=str)
    cleaned = text.replace("secret_redaction_passed", "").replace("secrets_emitted", "")
    return SECRET_RE.search(cleaned) is None
