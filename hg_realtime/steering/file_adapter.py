"""File-backed SteeringAdapter: appends each SteeringEvent to a JSONL file."""

from __future__ import annotations

import json
from pathlib import Path

from .adapter import SteeringAdapter
from .contracts import SteeringEvent


def _serialize_event(evt: SteeringEvent) -> str:
    return json.dumps({
        "steering_id": evt.steering_id,
        "tenant_id": evt.tenant_id,
        "actor_id": evt.actor_id,
        "correlation_id": evt.correlation_id,
        "run_id": evt.run_id,
        "node_id": evt.node_id,
        "kind": evt.kind,
        "payload": evt.payload,
        "created_at": evt.created_at.isoformat() if evt.created_at else None,
    }, default=str)


class FileSteeringAdapter(SteeringAdapter):
    """Appends each submitted SteeringEvent to path (JSONL)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def submit(self, evt: SteeringEvent) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(_serialize_event(evt) + "\n")
