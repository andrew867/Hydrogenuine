"""
Pack4: SSE event hub. When REDIS_URL is set, publish to Redis and run a subscriber thread
that fans out Redis messages to local queues so SSE works across gateway instances.
When REDIS_URL is not set, use in-memory stream_bus only.
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import Any, Dict, Tuple

from hg_gateway import stream_bus
from hg_core.events.publisher import publish as redis_publish
from hg_core.events.subscriber_redis import create_subscriber

_redis_thread: threading.Thread | None = None
_redis_started = False


def _fan_out_from_redis(chat_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    stream_bus.emit(chat_id, event_type, payload)


def _ensure_redis_subscriber() -> None:
    global _redis_thread, _redis_started
    if _redis_started or not os.environ.get("REDIS_URL", "").strip():
        return
    pubsub = create_subscriber(_fan_out_from_redis)
    if pubsub is None:
        return
    _redis_started = True
    _redis_thread = threading.Thread(target=pubsub._listen, daemon=True)
    _redis_thread.start()


def emit(chat_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """Emit to local subscribers and to Redis (if configured) for other instances."""
    stream_bus.emit(chat_id, event_type, payload)
    if os.environ.get("REDIS_URL", "").strip():
        _ensure_redis_subscriber()
        redis_publish(chat_id, event_type, payload)


def subscribe(chat_id: str) -> asyncio.Queue[Tuple[str, Dict[str, Any]]]:
    """Subscribe to events for chat_id. Uses local stream_bus (fed by Redis subscriber when REDIS_URL set)."""
    _ensure_redis_subscriber()
    return stream_bus.subscribe(chat_id)


def unsubscribe(chat_id: str, q: asyncio.Queue[Tuple[str, Dict[str, Any]]]) -> None:
    stream_bus.unsubscribe(chat_id, q)
