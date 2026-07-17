"""SteeringAdapter backed by the default steering store."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .adapter import SteeringAdapter
from .contracts import SteeringEvent
from .store import default_steering_store

if TYPE_CHECKING:
    pass


class SqliteSteeringAdapter(SteeringAdapter):
    """SteeringAdapter that persists to SQLite; use .store for get_pending()."""

    def __init__(self, db_path: str | None = None) -> None:
        self._store = default_steering_store(db_path=db_path)

    def submit(self, evt: SteeringEvent) -> None:
        self._store.submit(evt)

    @property
    def store(self):
        return self._store
