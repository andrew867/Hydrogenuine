"""
Pack3 Phase 5: Trace ID propagation — contextvar and request state.

Middleware sets trace_id from X-Request-ID header or generates one; stored in request.state and contextvar
so routes, orchestration, and tools can read it. Response includes X-Request-ID header.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_trace_id() -> str | None:
    """Return current request trace id (from contextvar)."""
    return trace_id_ctx.get()


def set_trace_id(value: str | None) -> None:
    """Set trace id in context (middleware or test)."""
    trace_id_ctx.set(value)


def get_request_id() -> str | None:
    """Return current request id (from contextvar). Pack 25: propagate for evidence tagging."""
    return request_id_ctx.get() or trace_id_ctx.get()


def set_request_id(value: str | None) -> None:
    """Set request id in context (middleware or test)."""
    request_id_ctx.set(value)


def generate_trace_id() -> str:
    """Generate a new trace id (e.g. UUID)."""
    return str(uuid.uuid4())
