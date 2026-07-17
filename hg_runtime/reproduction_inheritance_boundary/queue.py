"""RIB fake child bootstrap queue — slice 3, no live child."""

from __future__ import annotations

from typing import Any

from hg_core.rib_cluster.errors import RIB_FAKE_QUEUE_ENQUEUED, RibValidationError
from hg_core.rib_cluster.no_authority import advisory_only_marker
from hg_runtime.reproduction_inheritance_boundary.router import refuse_rib_as_authority
from hg_runtime.reproduction_inheritance_boundary.types import FIXTURE_CLOCK, SpawnRequest


class FakeChildBootstrapQueue:
    """In-memory fake queue for child bootstrap requests — advisory only."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    def enqueue(
        self,
        spawn_request: SpawnRequest,
        *,
        treat_as_authority: bool = False,
    ) -> dict[str, object]:
        if treat_as_authority:
            refuse_rib_as_authority(treat_as_authority=True)
        item = {
            "queue_id": f"rib-queue-{len(self._items) + 1}",
            "spawn_request": spawn_request.to_payload(),
            "enqueued_at": FIXTURE_CLOCK,
            "status": "queued",
            "permission_granted": False,
            "child_authority_created": False,
            "live_spawn": False,
        }
        self._items.append(item)
        return {
            **advisory_only_marker(),
            "status": "enqueued",
            "reason_code": RIB_FAKE_QUEUE_ENQUEUED,
            "queue_item": item,
            "queue_depth": len(self._items),
            "fake_queue_only": True,
            "permission_granted": False,
            "child_authority_created": False,
        }

    def peek(self) -> dict[str, Any] | None:
        if not self._items:
            return None
        return dict(self._items[0])

    def drain(self) -> list[dict[str, Any]]:
        items = list(self._items)
        self._items.clear()
        return items

    @property
    def depth(self) -> int:
        return len(self._items)


__all__ = ["FakeChildBootstrapQueue"]
