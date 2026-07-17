from __future__ import annotations
from abc import ABC, abstractmethod
from ..observability.contracts import TimelineEvent

class OperatorStream(ABC):
    """Interface for emitting timeline events. Concrete implementation: EventStoreOperatorStream."""

    @abstractmethod
    def emit(self, evt: TimelineEvent) -> None: ...
