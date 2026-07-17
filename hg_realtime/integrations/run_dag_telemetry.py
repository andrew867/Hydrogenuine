"""L10 telemetry sink: push executor timeline events to event store for GET /events/stream. Phase 9."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def make_l10_telemetry_sink(
    tenant_id: str = "default",
    actor_id: str = "executor",
) -> Optional[Callable[[str, Dict[str, Any]], None]]:
    """
    Return a telemetry sink that appends each (event_name, payload) to the L10 event store.
    Use when HG_EVENTS_DB_PATH or HG_DB_PATH is set so GET /events/stream sees timeline events.
    Returns None if event store is unavailable.
    """
    try:
        from hg_realtime.event_store import append_event
    except Exception:
        return None

    def sink(event_name: str, payload: Dict[str, Any]) -> None:
        try:
            run_id = payload.get("run_id") if isinstance(payload.get("run_id"), str) else None
            correlation_id = payload.get("correlation_id") or ""
            append_event(
                tenant_id=tenant_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                run_id=run_id,
                payload={"event": event_name, **payload},
                event_type="timeline",
            )
        except Exception:
            pass

    return sink
