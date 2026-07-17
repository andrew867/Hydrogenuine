"""
Pack4: Publish events to Redis for cross-instance fan-out.
When REDIS_URL is not set or redis is not installed, no-op.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

_CHANNEL = "hg:sse"


def publish(chat_id: str, event_type: str, payload: Dict[str, Any]) -> bool:
    """
    Publish event to Redis channel. Payload is JSON-serialized with chat_id and event_type.
    Returns True if published, False if Redis unavailable or not configured.
    """
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return False
    try:
        import redis
        r = redis.from_url(url)
        msg = json.dumps({"chat_id": chat_id, "event_type": event_type, "payload": payload})
        r.publish(_CHANNEL, msg)
        r.close()
        return True
    except Exception:
        return False
