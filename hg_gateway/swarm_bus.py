"""
Tenant-scoped in-memory bus for /v1/swarms/{swarm_run_id}/stream SSE subscribers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

_queues: Dict[str, List[asyncio.Queue[Tuple[str, Dict[str, Any]]]]] = {}


def _key(tenant_id: str, swarm_run_id: str) -> str:
    return f"{tenant_id}:{swarm_run_id}"


def subscribe(tenant_id: str, swarm_run_id: str) -> asyncio.Queue[Tuple[str, Dict[str, Any]]]:
    q: asyncio.Queue[Tuple[str, Dict[str, Any]]] = asyncio.Queue()
    _queues.setdefault(_key(tenant_id, swarm_run_id), []).append(q)
    return q


def unsubscribe(tenant_id: str, swarm_run_id: str, q: asyncio.Queue[Tuple[str, Dict[str, Any]]]) -> None:
    key = _key(tenant_id, swarm_run_id)
    if key in _queues:
        try:
            _queues[key].remove(q)
        except ValueError:
            pass


def emit(tenant_id: str, swarm_run_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    for q in _queues.get(_key(tenant_id, swarm_run_id), []):
        try:
            q.put_nowait((event_type, payload))
        except asyncio.QueueFull:
            pass
