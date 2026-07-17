"""
Pack4: Subscribe to Redis channel; sync get_message for use in a thread that fans out to local queues.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional, Tuple

_CHANNEL = "hg:sse"


def _redis_url() -> Optional[str]:
    return os.environ.get("REDIS_URL", "").strip() or None


def create_subscriber(callback: Callable[[str, str, Dict[str, Any]], None]) -> Optional[Any]:
    """
    Create a Redis pubsub subscriber that calls callback(chat_id, event_type, payload) for each message.
    Returns the pubsub object (so caller can run listen() in a thread) or None if Redis unavailable.
    """
    url = _redis_url()
    if not url:
        return None
    try:
        import redis
        r = redis.from_url(url)
        pubsub = r.pubsub()
        pubsub.subscribe(_CHANNEL)

        def _listen() -> None:
            for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue
                data = msg.get("data")
                if not data:
                    continue
                try:
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    obj = json.loads(data)
                    callback(
                        obj.get("chat_id") or "",
                        obj.get("event_type") or "event",
                        obj.get("payload") or {},
                    )
                except (json.JSONDecodeError, TypeError):
                    continue

        pubsub._listen = _listen
        return pubsub
    except Exception:
        return None
