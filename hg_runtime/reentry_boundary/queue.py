"""REB fake re-entry queue — slice 3, no live resume."""

from __future__ import annotations

from typing import Any

from hg_core.reb_cluster.errors import REB_FAKE_QUEUE_ENQUEUED, RebValidationError
from hg_core.reb_cluster.no_authority import advisory_only_marker
from hg_runtime.reentry_boundary.types import FIXTURE_CLOCK, ReEntryRequest


class FakeReEntryQueue:
    """In-memory fake queue for re-entry requests — advisory only."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    def enqueue(
        self,
        reentry_request: ReEntryRequest,
        *,
        treat_as_authority: bool = False,
    ) -> dict[str, object]:
        if treat_as_authority:
            raise RebValidationError(
                "reb.refused.reentry_as_authority",
                "fake queue cannot grant authority",
            )
        item = {
            "queue_id": f"reb-queue-{len(self._items) + 1}",
            "reentry_request": reentry_request.to_payload(),
            "enqueued_at": FIXTURE_CLOCK,
            "status": "queued",
            "permission_granted": False,
            "live_resume": False,
        }
        self._items.append(item)
        return {
            **advisory_only_marker(),
            "status": "enqueued",
            "reason_code": REB_FAKE_QUEUE_ENQUEUED,
            "queue_item": item,
            "queue_depth": len(self._items),
            "fake_queue_only": True,
            "permission_granted": False,
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


__all__ = ["FakeReEntryQueue"]
