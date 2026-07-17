"""U4 operator runs-list SSE delta generator."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))

from app.services.runs_list_stream import stream_runs_list  # noqa: E402


def test_stream_runs_list_emits_initial_delta():
    async def _collect_first():
        gen = stream_runs_list(limit=10, interval_sec=0.01)
        frame = await gen.__anext__()
        await gen.aclose()
        return frame

    frame = asyncio.run(_collect_first())
    assert "event: runs.delta" in frame
    assert "id: runs-list-" in frame
    data_line = next(line for line in frame.split("\n") if line.startswith("data: "))
    payload = json.loads(data_line[6:])
    assert "runs" in payload
