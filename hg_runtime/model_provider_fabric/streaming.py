"""Streaming token bus events — advisory metadata on every event."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from hg_runtime.model_provider_fabric.types import ModelProviderRole, advisory_envelope

StreamEventKind = Literal[
    "MODEL_RESPONSE_STARTED",
    "MODEL_RESPONSE_DELTA",
    "MODEL_RESPONSE_COMPLETED",
    "MODEL_RESPONSE_FAILED",
    "MODEL_PROVIDER_HEARTBEAT",
    "MODEL_PROVIDER_RECEIPT",
]


@dataclass(frozen=True)
class ModelTokenEvent:
    event_kind: StreamEventKind
    provider_id: str
    model_id: str
    role: ModelProviderRole
    organ_id: str | None
    request_id: str
    sequence: int
    delta_text: str = ""
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="model-token-event",
            event_kind=self.event_kind,
            provider_id=self.provider_id,
            model_id=self.model_id,
            role=self.role,
            organ_id=self.organ_id,
            request_id=self.request_id,
            sequence=self.sequence,
            delta_text=self.delta_text,
            error=self.error,
        )


def emit_non_streaming_as_events(
    *,
    provider_id: str,
    model_id: str,
    role: ModelProviderRole,
    organ_id: str | None,
    request_id: str,
    full_text: str,
    prompt: str | None = None,
) -> list[ModelTokenEvent]:
    from hg_runtime.model_provider_fabric.watchtower_adapter import WatchtowerInferenceContext

    events = [
        ModelTokenEvent("MODEL_RESPONSE_STARTED", provider_id, model_id, role, organ_id, request_id, 0),
    ]
    with WatchtowerInferenceContext(
        provider_id=provider_id,
        model_id=model_id,
        request_id=request_id,
        organ_id=organ_id,
        task_id=f"mpf:{role}",
        prompt=prompt,
    ) as ctx:
        if full_text:
            ctx.chunk(full_text)
        events.append(
            ModelTokenEvent(
                "MODEL_RESPONSE_DELTA",
                provider_id,
                model_id,
                role,
                organ_id,
                request_id,
                1,
                delta_text=full_text,
            )
        )
        events.append(
            ModelTokenEvent("MODEL_RESPONSE_COMPLETED", provider_id, model_id, role, organ_id, request_id, 2)
        )
    return events


def emit_stream_delta(
    *,
    provider_id: str,
    model_id: str,
    role: ModelProviderRole,
    organ_id: str | None,
    request_id: str,
    sequence: int,
    delta_text: str,
    span_id: str | None = None,
) -> ModelTokenEvent:
    from hg_runtime.model_provider_fabric.watchtower_adapter import WatchtowerInferenceContext

    if span_id:
        ctx = WatchtowerInferenceContext(
            provider_id=provider_id,
            model_id=model_id,
            request_id=request_id,
            organ_id=organ_id,
        )
        ctx.span_id = span_id
        ctx.chunk(delta_text)
    return ModelTokenEvent(
        "MODEL_RESPONSE_DELTA",
        provider_id,
        model_id,
        role,
        organ_id,
        request_id,
        sequence,
        delta_text=delta_text,
    )


def emit_inference_failed(
    *,
    provider_id: str,
    model_id: str,
    role: ModelProviderRole,
    organ_id: str | None,
    request_id: str,
    sequence: int,
    error: str,
) -> ModelTokenEvent:
    from hg_runtime.openvino_watchtower.collector import get_collector
    from hg_runtime.openvino_watchtower.events import watchtower_enabled

    if watchtower_enabled():
        try:
            collector = get_collector()
            for span in collector.build_state().get("active_inference_spans") or []:
                sid = span.span_id if hasattr(span, "span_id") else span.get("span_id")
                rid = span.request_id if hasattr(span, "request_id") else span.get("request_id")
                if rid == request_id and sid:
                    collector.fail_inference(sid, error=error)
                    break
        except Exception:
            pass
    return ModelTokenEvent(
        "MODEL_RESPONSE_FAILED",
        provider_id,
        model_id,
        role,
        organ_id,
        request_id,
        sequence,
        error=error,
    )


__all__ = ["ModelTokenEvent", "StreamEventKind", "emit_inference_failed", "emit_non_streaming_as_events", "emit_stream_delta"]
