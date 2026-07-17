"""
Control Surface Pack 4: Rate limiting for control endpoints.
Per user/tenant sliding window; configurable requests per minute.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict

_lock = threading.Lock()
_buckets: Dict[str, deque] = {}


def check_rate_limit(
    key: str,
    *,
    requests_per_minute: int = 60,
    window_seconds: int = 60,
) -> bool:
    """
    Check if request is within rate limit. Key is typically actor_id or tenant_id.
    Returns True if allowed, False if rate limited.
    Caller should record_api_request(success=False, rate_limited=True) when False.
    """
    now = time.monotonic()
    with _lock:
        if key not in _buckets:
            _buckets[key] = deque(maxlen=max(requests_per_minute * 2, 1))
        q = _buckets[key]
        while q and q[0] < now - window_seconds:
            q.popleft()
        if len(q) >= requests_per_minute:
            return False
        q.append(now)
    return True


def is_dangerous_control(action: str) -> bool:
    """True if control action requires step-up auth (override, handoff, quorum-related)."""
    dangerous = (
        "control/override",
        "control/handoff",
        "control/pause",
        "control/resume",
        "steering/goal",
        "steering/autonomy",
    )
    return any(action.endswith(a) or a in action for a in dangerous)


def require_step_up_auth(actor: Dict[str, Any], action: str) -> bool:
    """
    Return True if actor has satisfied step-up auth for this action (e.g. quorum or MFA).
    Deny by default on ambiguous permissions. Stub: checks env HG_CONTROL_STEP_UP=1 to allow.
    """
    if not is_dangerous_control(action):
        return True
    import os
    if os.environ.get("HG_CONTROL_STEP_UP") == "1":
        return True
    if actor.get("key_id") and actor.get("key_id") != "default":
        return True
    return False
