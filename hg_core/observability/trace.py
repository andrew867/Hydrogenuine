"""
Trace ID propagation for request -> ledger -> materializers -> tool execution.
Thread-local or context var so subsystems can attach trace_id to events.
"""
from __future__ import annotations

import threading
import uuid
from typing import Optional

_trace_id: threading.local = threading.local()


def get_trace_id() -> Optional[str]:
    """Return current trace ID for this thread/context."""
    return getattr(_trace_id, "value", None)


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """Set trace ID; if None, generate new. Returns the trace_id."""
    tid = trace_id or str(uuid.uuid4())
    _trace_id.value = tid
    return tid
