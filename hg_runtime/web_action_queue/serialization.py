"""Serialization helpers."""

from __future__ import annotations

import json

from hg_runtime.web_action_queue.schema import WebActionQueue, WebActionRequest


def request_to_json(req: WebActionRequest, *, indent: int = 2) -> str:
    return json.dumps(req.to_payload(), indent=indent, sort_keys=True)


def queue_to_json(queue: WebActionQueue, *, indent: int = 2) -> str:
    return json.dumps(queue.to_payload(), indent=indent, sort_keys=True)


__all__ = ["queue_to_json", "request_to_json"]
