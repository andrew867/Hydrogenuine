from __future__ import annotations
from abc import ABC, abstractmethod
from .contracts import SteeringEvent

class SteeringAdapter(ABC):
    """Interface for submitting steering events. Concrete implementations: SqliteSteeringAdapter, FileSteeringAdapter."""

    @abstractmethod
    def submit(self, evt: SteeringEvent) -> None: ...
