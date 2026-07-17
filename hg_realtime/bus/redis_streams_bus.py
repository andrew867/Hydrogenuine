"""Redis Streams implementation of EventBus. Production-ready; requires redis-py."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .interface import EventBus
from ..schemas.event import Event


def _default_json_serializer(obj: object) -> str:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class RedisStreamsBus(EventBus):
    """Redis Streams adapter. One stream per bus, consumer groups, XADD/XREADGROUP/XACK."""

    def __init__(
        self,
        *,
        redis_url: str = "redis://localhost/0",
        stream: str = "hg:events",
        max_len: Optional[int] = None,
        client: Any = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            import redis
            self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._stream = stream
        self._max_len = max_len
        self._pending: Dict[str, str] = {}  # event_id -> redis message id

    def _ensure_consumer_group(self, group: str) -> None:
        try:
            self._client.xgroup_create(
                self._stream,
                group,
                id="0",
                mkstream=True,
            )
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                raise

    def publish(self, event: Event) -> None:
        event.validate()
        body = json.dumps(event.to_dict(), default=_default_json_serializer)
        kwargs = {}
        if self._max_len is not None:
            kwargs["maxlen"] = self._max_len
            kwargs["approximate"] = True
        self._client.xadd(self._stream, {"payload": body}, **kwargs)

    def poll(
        self,
        *,
        group: str,
        consumer: str,
        max_events: int = 50,
        timeout_s: float = 1.0,
    ) -> list[Event]:
        self._ensure_consumer_group(group)
        timeout_ms = max(1, int(timeout_s * 1000))
        raw = self._client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={self._stream: ">"},
            count=max_events,
            block=timeout_ms,
        )
        self._pending.clear()
        out: list[Event] = []
        if not raw:
            return out
        for stream_name, messages in raw:
            if stream_name != self._stream:
                continue
            for msg_id, fields in messages:
                payload_str = (fields or {}).get("payload") if isinstance(fields, dict) else None
                if not payload_str:
                    continue
                try:
                    data = json.loads(payload_str)
                    if isinstance(data, dict) and "event_id" in data and "payload" in data:
                        ev = Event.from_dict(data)
                        self._pending[ev.event_id] = msg_id
                        out.append(ev)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return out

    def ack(self, *, group: str, consumer: str, event_id: str) -> None:
        redis_id = self._pending.pop(event_id, None)
        if redis_id is None:
            return
        self._client.xack(self._stream, group, redis_id)
