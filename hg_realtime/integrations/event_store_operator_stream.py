"""Concrete OperatorStream that writes TimelineEvent to L10 event store (Phase 9)."""

from __future__ import annotations

from ..observability.contracts import TimelineEvent
from .operator_stream import OperatorStream


class EventStoreOperatorStream(OperatorStream):
    """Emit timeline events to the L10 event store so GET /events/stream sees them."""

    def __init__(
        self,
        tenant_id: str = "default",
        actor_id: str = "executor",
    ) -> None:
        self._tenant_id = tenant_id
        self._actor_id = actor_id

    def emit(self, evt: TimelineEvent) -> None:
        try:
            from hg_realtime.event_store import append_event
            append_event(
                tenant_id=self._tenant_id,
                actor_id=self._actor_id,
                correlation_id=evt.correlation_id or "",
                run_id=evt.run_id,
                payload={"kind": evt.kind, **evt.data},
                event_type="timeline",
            )
        except Exception:
            pass
