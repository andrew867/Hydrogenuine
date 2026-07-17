"""
Tenant-scoped in-memory bus for /v1/stream/notifications SSE subscribers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

_queues: Dict[str, List[asyncio.Queue[Tuple[str, Dict[str, Any]]]]] = {}


def subscribe(tenant_id: str) -> asyncio.Queue[Tuple[str, Dict[str, Any]]]:
    q: asyncio.Queue[Tuple[str, Dict[str, Any]]] = asyncio.Queue()
    _queues.setdefault(tenant_id, []).append(q)
    return q


def unsubscribe(tenant_id: str, q: asyncio.Queue[Tuple[str, Dict[str, Any]]]) -> None:
    if tenant_id in _queues:
        try:
            _queues[tenant_id].remove(q)
        except ValueError:
            pass


def emit(tenant_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    for q in _queues.get(tenant_id, []):
        try:
            q.put_nowait((event_type, payload))
        except asyncio.QueueFull:
            pass
