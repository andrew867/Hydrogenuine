"""SSE stream for operator runs-list deltas (snapshot when index changes)."""

from __future__ import annotations

import asyncio
import hashlib
import json

from .run_ops import list_runs


async def stream_runs_list(*, limit: int = 200, interval_sec: float = 5.0):
    """Yield SSE runs.delta events when the runs list snapshot changes."""
    last_hash: str | None = None
    seq = 0
    while True:
        payload = list_runs(limit=limit)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        if digest != last_hash:
            last_hash = digest
            seq += 1
            data = json.dumps(payload)
            yield f"id: runs-list-{seq}\nevent: runs.delta\ndata: {data}\n\n"
        await asyncio.sleep(interval_sec)
