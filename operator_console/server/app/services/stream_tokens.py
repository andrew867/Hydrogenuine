"""Short-lived tokens for SSE streams (EventSource cannot send Authorization headers)."""

from __future__ import annotations

import secrets
import time
from typing import Dict, Tuple

_TOKENS: Dict[str, Tuple[str, float]] = {}


def mint_stream_token(run_id: str, ttl_sec: int = 120) -> str:
    token = secrets.token_urlsafe(24)
    _TOKENS[token] = (run_id, time.time() + ttl_sec)
    return token


def validate_stream_token(token: str, run_id: str) -> bool:
    if not token:
        return False
    row = _TOKENS.get(token)
    if not row:
        return False
    stored_run_id, exp = row
    if time.time() > exp:
        _TOKENS.pop(token, None)
        return False
    if stored_run_id != run_id:
        return False
    return True
