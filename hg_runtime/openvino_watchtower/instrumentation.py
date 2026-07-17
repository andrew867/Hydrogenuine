"""Provider instrumentation hooks — wrap model provider calls with watchtower spans."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator, Iterator

from hg_runtime.openvino_watchtower.collector import get_collector
from hg_runtime.openvino_watchtower.events import watchtower_enabled, watchtower_strict
from hg_runtime.openvino_watchtower.errors import WatchtowerStrictError
from hg_runtime.openvino_watchtower.schema import InferenceSpan


def _enabled() -> bool:
    return watchtower_enabled()


@contextmanager
def inference_span(
    *,
    organ_id: str | None = None,
    task: str | None = None,
    model_id: str | None = None,
    device: str | None = None,
    request_id: str | None = None,
    prompt_text: str | None = None,
    action_id: str | None = None,
    queue_item_ref: str | None = None,
    authority_chain_ref: str | None = None,
) -> Iterator[InferenceSpan | None]:
    if not _enabled():
        yield None
        return
    try:
        collector = get_collector()
        span = collector.begin_inference(
            request_id=request_id,
            organ_id=organ_id,
            task=task,
            model_id=model_id,
            device=device,
            action_id=action_id,
            prompt_text=prompt_text,
            queue_item_ref=queue_item_ref,
            authority_chain_ref=authority_chain_ref,
        )
    except Exception as exc:
        if watchtower_strict():
            raise WatchtowerStrictError(str(exc)) from exc
        yield None
        return
    try:
        yield span
        collector.complete_inference(span.span_id)
    except Exception as exc:
        collector.fail_inference(span.span_id, error=str(exc))
        raise


def hook_model_load_started(**kwargs: Any) -> None:
    if not _enabled():
        return
    get_collector().on_model_load_started(**kwargs)


def hook_model_load_completed(**kwargs: Any) -> None:
    if not _enabled():
        return
    get_collector().on_model_load_completed(**kwargs)


def hook_model_load_failed(**kwargs: Any) -> None:
    if not _enabled():
        return
    get_collector().on_model_load_failed(**kwargs)


def hook_compile_started(**kwargs: Any) -> None:
    if not _enabled():
        return
    get_collector().on_compile_started(**kwargs)


def hook_compile_completed(**kwargs: Any) -> None:
    if not _enabled():
        return
    get_collector().on_compile_completed(**kwargs)


def hook_compile_failed(**kwargs: Any) -> None:
    if not _enabled():
        return
    get_collector().on_compile_failed(**kwargs)


def hook_chunk(span_id: str, *, delta: str = "", token_count: int = 0) -> None:
    if not _enabled():
        return
    get_collector().on_chunk(span_id, delta=delta, token_count=token_count)


def maybe_autostart_watchtower() -> None:
    """Explicit autostart via runtime config — local-only, non-authoritative."""
    from hg_runtime.openvino_watchtower.lifecycle import maybe_autostart_watchtower as _lifecycle_autostart

    _lifecycle_autostart()


class WatchtowerStreamingAdapter:
    """Wrap token events from model_provider_fabric.streaming."""

    def __init__(self, span: InferenceSpan | None) -> None:
        self.span = span

    def on_delta(self, delta: str) -> None:
        if self.span:
            hook_chunk(self.span.span_id, delta=delta, token_count=max(1, len(delta.split())))


__all__ = [
    "WatchtowerStreamingAdapter",
    "hook_chunk",
    "hook_compile_completed",
    "hook_compile_failed",
    "hook_compile_started",
    "hook_model_load_completed",
    "hook_model_load_failed",
    "hook_model_load_started",
    "inference_span",
    "maybe_autostart_watchtower",
]
