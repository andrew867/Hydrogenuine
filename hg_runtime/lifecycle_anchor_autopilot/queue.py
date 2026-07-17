"""Operator queue for lifecycle anchor autopilot."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from hg_runtime.lifecycle_anchor_autopilot.schema import AnchorAutopilotQueueItem

WORKSPACE = Path(__file__).resolve().parents[2]
QUEUE_PATH = WORKSPACE / ".hg-local/lifecycle_anchor_autopilot/operator_queue.json"


def _load() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8")).get("items", [])


def _save(items: list[dict[str, Any]]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps({"schema": "anchor-autopilot-queue", "items": items}, indent=2), encoding="utf-8")


def enqueue(item: AnchorAutopilotQueueItem) -> str:
    items = _load()
    payload = item.to_payload()
    items.append(payload)
    _save(items)
    return item.item_id


def list_queue() -> list[dict[str, Any]]:
    return _load()


def flush_queue() -> list[dict[str, Any]]:
    items = _load()
    _save([])
    return items
