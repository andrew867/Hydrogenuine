from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from hg_realtime.bus.interface import EventBus
from hg_realtime.schemas.event import Event, EventType, stable_event_id

logger = logging.getLogger(__name__)

REFLECTION_CYCLE_STARTED = "reflection_cycle_started"
REFLECTION_CYCLE_COMPLETED = "reflection_cycle_completed"
REFLECTION_CYCLE_FAILED = "reflection_cycle_failed"


class ReflectionWorker:
    """Runs reflection cycles on a cooldown-aware tick and emits simple telemetry events."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        bus: EventBus | None = None,
        worker_id: str = "reflection-1",
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.bus = bus
        self.worker_id = worker_id
        self.group = "hg-reflection"
        self.consumer = worker_id

    def _emit(self, *, kind: str, payload: dict[str, Any]) -> None:
        if self.bus is None:
            return
        tenant_id = str(payload.get("tenant_id") or "default")
        actor_id = str(payload.get("actor_id") or "system")
        correlation_id = str(payload.get("correlation_id") or f"reflection:{self.worker_id}")
        dedup_key = f"{kind}:{correlation_id}:{payload.get('ts') or ''}"
        event_payload = {"kind": kind, **payload}
        eid = stable_event_id("internal", tenant_id, dedup_key, event_payload)
        self.bus.publish(
            Event(
                event_id=eid,
                event_type=EventType.INTERNAL,
                tenant_id=tenant_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                payload=event_payload,
                dedup_key=dedup_key,
            )
        )

    def tick_once(self, *, force: bool = False) -> dict[str, Any]:
        from operator_console.server.app.services.reflection_cycle_service import run_reflection_cycles

        self._emit(kind=REFLECTION_CYCLE_STARTED, payload={"ts": None, "tenant_id": "default", "actor_id": self.worker_id})
        try:
            result = run_reflection_cycles(self.workspace_root, force=force)
        except Exception as exc:
            logger.exception("reflection worker failed")
            payload = {
                "ts": None,
                "tenant_id": "default",
                "actor_id": self.worker_id,
                "error": str(exc),
            }
            self._emit(kind=REFLECTION_CYCLE_FAILED, payload=payload)
            return {"ok": False, "cycles": [], "errors": [{"cycle": "worker", "error": str(exc)}]}

        cycles = result.get("cycles") if isinstance(result, dict) else []
        errors = result.get("errors") if isinstance(result, dict) else []
        if cycles:
            self._emit(
                kind=REFLECTION_CYCLE_COMPLETED,
                payload={
                    "ts": result.get("ts"),
                    "tenant_id": "default",
                    "actor_id": self.worker_id,
                    "cycles": cycles,
                },
            )
        if errors:
            self._emit(
                kind=REFLECTION_CYCLE_FAILED,
                payload={
                    "ts": result.get("ts"),
                    "tenant_id": "default",
                    "actor_id": self.worker_id,
                    "errors": errors,
                },
            )
        return result
