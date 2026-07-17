"""
Pack4: Horizontal scaling and degraded mode tests.
When REDIS_URL unset, sse_hub uses local stream_bus only (degraded mode).
"""

import os
import pytest
from hg_gateway import sse_hub


def test_sse_hub_emit_subscribe_without_redis():
    """sse_hub emit and subscribe work without REDIS_URL (local only)."""
    os.environ.pop("REDIS_URL", None)
    q = sse_hub.subscribe("chat_local")
    sse_hub.emit("chat_local", "test.event", {"data": 1})
    # Queue is asyncio.Queue; in sync test use get_nowait if queue not empty
    try:
        ev, pl = q.get_nowait()
        assert ev == "test.event"
        assert pl == {"data": 1}
    except Exception:
        import asyncio
        ev, pl = asyncio.run(asyncio.wait_for(q.get(), timeout=2.0))
        assert ev == "test.event"
        assert pl == {"data": 1}
