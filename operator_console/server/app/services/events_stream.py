"""SSE stream from run_dir/events.jsonl."""

from pathlib import Path
from .run_index_db import get_run


def _run_dir(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])


def stream_events(run_id: str):
    """Yield SSE events: first event: ready, then event: line per line from run_dir/events.jsonl."""
    yield "event: ready\ndata: {}\n\n"
    try:
        rd = _run_dir(run_id)
    except FileNotFoundError:
        return
    path = rd / "events.jsonl"
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line:
                yield f"event: line\ndata: {line}\n\n"
