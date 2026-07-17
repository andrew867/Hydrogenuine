from __future__ import annotations
from abc import ABC, abstractmethod
from ..schemas.event import Event

class EventBus(ABC):
    """Durable event stream interface.

    Implementations should provide at-least-once delivery.
    Consumers should be idempotent.

    Concrete implementations: RedisStreamsBus, InMemoryBus.
    """

    @abstractmethod
    def publish(self, event: Event) -> None: ...

    @abstractmethod
    def poll(self, *, group: str, consumer: str, max_events: int = 50, timeout_s: float = 1.0) -> list[Event]: ...

    @abstractmethod
    def ack(self, *, group: str, consumer: str, event_id: str) -> None: ...
