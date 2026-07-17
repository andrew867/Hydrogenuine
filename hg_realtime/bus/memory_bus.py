from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple
from .interface import EventBus
from ..schemas.event import Event

@dataclass
class _Envelope:
    event: Event
    ts: float

class InMemoryBus(EventBus):
    """In-memory bus for tests and local demos.

    Not durable, single-process only.
    """
    def __init__(self) -> None:
        self._q: Deque[_Envelope] = deque()
        self._inflight: Dict[Tuple[str, str, str], _Envelope] = {}

    def publish(self, event: Event) -> None:
        event.validate()
        self._q.append(_Envelope(event=event, ts=time.time()))

    def poll(self, *, group: str, consumer: str, max_events: int = 50, timeout_s: float = 1.0) -> list[Event]:
        deadline = time.time() + timeout_s
        out: list[Event] = []
        while time.time() < deadline and len(out) < max_events:
            if not self._q:
                time.sleep(0.01)
                continue
            env = self._q.popleft()
            key = (group, consumer, env.event.event_id)
            self._inflight[key] = env
            out.append(env.event)
        return out

    def ack(self, *, group: str, consumer: str, event_id: str) -> None:
        key = (group, consumer, event_id)
        self._inflight.pop(key, None)
