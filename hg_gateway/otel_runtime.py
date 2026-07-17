from __future__ import annotations

import os
from typing import Any, Dict, Optional

_enabled = False
_configured = False
_import_error: Optional[str] = None
_tracer = None
_provider = None
_exporter_endpoint: Optional[str] = None
_service_name = "hg-gateway"


def _headers_from_env(value: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in (value or "").split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, raw = part.split("=", 1)
        if key.strip():
            out[key.strip()] = raw.strip()
    return out


def _resolve_endpoint() -> Optional[str]:
    traces = (os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or "").strip()
    if traces:
        return traces
    base = (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    if not base:
        return None
    if base.endswith("/v1/traces"):
        return base
    return base.rstrip("/") + "/v1/traces"


def configure_otel(force: bool = False) -> None:
    global _enabled, _configured, _import_error, _tracer, _provider, _exporter_endpoint, _service_name
    if _configured and not force:
        return
    if force:
        shutdown_otel()
        _enabled = False
        _configured = False
        _import_error = None
        _tracer = None
        _provider = None
        _exporter_endpoint = None
    _configured = True
    _service_name = (os.getenv("OTEL_SERVICE_NAME") or "hg-gateway").strip() or "hg-gateway"
    endpoint = _resolve_endpoint()
    _exporter_endpoint = endpoint
    if not endpoint:
        _enabled = False
        return
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception as exc:
        _enabled = False
        _import_error = str(exc)
        return
    headers = _headers_from_env(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
    resource = Resource.create(
        {
            "service.name": _service_name,
            "service.version": "0.1",
        }
    )
    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers or None)
    schedule_delay = max(10, int((os.getenv("HG_OTEL_SCHEDULE_DELAY_MS") or "200").strip()))
    _provider = TracerProvider(resource=resource)
    _provider.add_span_processor(BatchSpanProcessor(exporter, schedule_delay_millis=schedule_delay))
    _tracer = _provider.get_tracer("hg_gateway.http")
    _enabled = True


def get_http_tracer():
    if not _configured:
        configure_otel()
    return _tracer if _enabled else None


def shutdown_otel() -> None:
    global _provider
    if _provider is not None:
        try:
            _provider.shutdown()
        except Exception:
            pass


def runtime_diagnostics() -> Dict[str, Any]:
    if not _configured:
        configure_otel()
    return {
        "enabled": _enabled,
        "endpoint": _exporter_endpoint,
        "service_name": _service_name,
        "import_error": _import_error,
    }
