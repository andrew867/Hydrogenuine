"""Serialization helpers for operator action queue."""

from __future__ import annotations

import json

from hg_runtime.operator_action_queue.schema import OperatorActionQueue, OperatorQueueItem, OperatorQueueSummary


def queue_to_json(queue: OperatorActionQueue, *, indent: int | None = 2) -> str:
    return json.dumps(queue.to_payload(), indent=indent, sort_keys=True)


def queue_from_json(text: str) -> OperatorActionQueue:
    return OperatorActionQueue.from_payload(json.loads(text))


def item_to_json(item: OperatorQueueItem, *, indent: int | None = 2) -> str:
    return json.dumps(item.to_payload(), indent=indent, sort_keys=True)


def summary_to_json(summary: OperatorQueueSummary, *, indent: int | None = 2) -> str:
    return json.dumps(summary.to_payload(), indent=indent, sort_keys=True)


__all__ = ["item_to_json", "queue_from_json", "queue_to_json", "summary_to_json"]
