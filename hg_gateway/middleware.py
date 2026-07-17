"""
Pack3 Phase 5: Request ID / trace ID middleware.

Accepts X-Request-ID from client or generates one; sets request.state.trace_id and contextvar;
adds X-Request-ID to response headers.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from hg_gateway.otel_runtime import get_http_tracer
from hg_gateway.trace_context import get_trace_id, set_trace_id, set_request_id, generate_trace_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Set or generate X-Request-ID; propagate via request.state and contextvar; add to response. Pack 25: request_id same as trace_id."""

    async def dispatch(self, request: Request, call_next: callable) -> Response:
        raw = request.headers.get("X-Request-ID") or request.headers.get("X-Trace-ID")
        trace_id = (raw.strip() if raw and isinstance(raw, str) else None) or generate_trace_id()
        request.state.trace_id = trace_id
        request.state.request_id = trace_id
        set_trace_id(trace_id)
        set_request_id(trace_id)
        tracer = get_http_tracer()
        span_name = f"{request.method} {request.url.path}"
        try:
            if tracer is None:
                response = await call_next(request)
            else:
                with tracer.start_as_current_span(span_name) as span:
                    span.set_attribute("http.method", request.method)
                    span.set_attribute("http.route", request.url.path)
                    span.set_attribute("http.target", str(request.url))
                    span.set_attribute("hg.request_id", trace_id)
                    response = await call_next(request)
                    span.set_attribute("http.status_code", int(response.status_code))
            response.headers["X-Request-ID"] = trace_id
            from hg_gateway.metrics import record_request
            record_request(success=response.status_code < 400, trace_id=trace_id)
            return response
        finally:
            set_trace_id(None)
