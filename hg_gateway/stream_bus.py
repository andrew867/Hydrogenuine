"""
Simple in-memory bus for SSE/WS: per-chat queues so run_turn can emit to all subscribers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

_queues: Dict[str, List[asyncio.Queue[Tuple[str, Dict[str, Any]]]]] = {}


def subscribe(chat_id: str) -> asyncio.Queue[Tuple[str, Dict[str, Any]]]:
    q: asyncio.Queue[Tuple[str, Dict[str, Any]]] = asyncio.Queue()
    _queues.setdefault(chat_id, []).append(q)
    return q


def unsubscribe(chat_id: str, q: asyncio.Queue[Tuple[str, Dict[str, Any]]]) -> None:
    if chat_id in _queues:
        try:
            _queues[chat_id].remove(q)
        except ValueError:
            pass


def emit(chat_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    for q in _queues.get(chat_id, []):
        try:
            q.put_nowait((event_type, payload))
        except asyncio.QueueFull:
            pass
