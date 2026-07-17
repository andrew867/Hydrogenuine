"""Model provider fabric → OpenVINO Watchtower telemetry adapter."""

from __future__ import annotations

import hashlib
from typing import Any

from hg_runtime.openvino_watchtower.provider_hooks_config import load_provider_hooks_config


def _cfg():
    return load_provider_hooks_config()


def _safe_call(fn, *args, **kwargs) -> None:
    cfg = _cfg()
    if not cfg.enabled:
        return
    try:
        fn(*args, **kwargs)
    except Exception:
        if cfg.strict_mode:
            raise


def hooks_enabled() -> bool:
    return _cfg().enabled


def strict_mode() -> bool:
    return _cfg().strict_mode


def payload_hash(text: str) -> str | None:
    cfg = _cfg()
    if not cfg.capture_payload_hash or not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def safe_prompt_meta(prompt: str | None) -> dict[str, Any]:
    cfg = _cfg()
    if cfg.capture_raw_prompt and prompt:
        return {"prompt_text": prompt}
    return {}


def on_model_load_started(*, model_id: str, model_path: str | None = None, **extra: Any) -> None:
    from hg_runtime.openvino_watchtower.instrumentation import hook_model_load_started

    _safe_call(hook_model_load_started, model_id=model_id, model_path=model_path, **extra)


def on_model_load_completed(*, model_id: str, duration_ms: float = 0.0, model_hash: str | None = None, **extra: Any) -> None:
    from hg_runtime.openvino_watchtower.instrumentation import hook_model_load_completed

    _safe_call(hook_model_load_completed, model_id=model_id, duration_ms=duration_ms, model_hash=model_hash, **extra)


def on_model_load_failed(*, model_id: str, error: str, **extra: Any) -> None:
    from hg_runtime.openvino_watchtower.instrumentation import hook_model_load_failed

    _safe_call(hook_model_load_failed, model_id=model_id, error=error, **extra)


def on_compile_started(*, model_id: str, device: str) -> None:
    from hg_runtime.openvino_watchtower.instrumentation import hook_compile_started

    _safe_call(hook_compile_started, model_id=model_id, device=device)


def on_compile_completed(*, model_id: str, device: str, duration_ms: float = 0.0) -> None:
    from hg_runtime.openvino_watchtower.instrumentation import hook_compile_completed

    _safe_call(hook_compile_completed, model_id=model_id, device=device, duration_ms=duration_ms)


def on_compile_failed(*, model_id: str, device: str, error: str) -> None:
    from hg_runtime.openvino_watchtower.instrumentation import hook_compile_failed

    _safe_call(hook_compile_failed, model_id=model_id, device=device, error=error)


class WatchtowerInferenceContext:
    """Context manager wrapping a model-provider inference call."""

    def __init__(
        self,
        *,
        provider_id: str,
        model_id: str,
        request_id: str,
        organ_id: str | None = None,
        task_id: str | None = None,
        prompt: str | None = None,
        device: str | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.request_id = request_id
        self.organ_id = organ_id
        self.task_id = task_id
        self.prompt = prompt
        self.device = device
        self.span_id: str | None = None
        self._cm = None
        self._span = None

    def __enter__(self) -> "WatchtowerInferenceContext":
        from hg_runtime.openvino_watchtower.instrumentation import inference_span

        if not _cfg().enabled:
            return self
        meta = safe_prompt_meta(self.prompt)
        try:
            self._cm = inference_span(
                organ_id=self.organ_id,
                task=self.task_id,
                model_id=self.model_id,
                device=self.device or self.provider_id,
                request_id=self.request_id,
                prompt_text=meta.get("prompt_text"),
            )
            self._span = self._cm.__enter__()
            if self._span is not None:
                self.span_id = self._span.span_id
        except Exception:
            if _cfg().strict_mode:
                raise
            self._cm = None
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._cm is None:
            return False
        return self._cm.__exit__(exc_type, exc, tb)

    def chunk(self, delta: str) -> None:
        if not self.span_id:
            return
        from hg_runtime.openvino_watchtower.instrumentation import hook_chunk

        cfg = _cfg()
        if not cfg.capture_chunks:
            return
        _safe_call(hook_chunk, self.span_id, delta=delta, token_count=max(1, len(delta.split())) if delta else 0)


__all__ = [
    "WatchtowerInferenceContext",
    "hooks_enabled",
    "on_compile_completed",
    "on_compile_failed",
    "on_compile_started",
    "on_model_load_completed",
    "on_model_load_failed",
    "on_model_load_started",
    "payload_hash",
    "safe_prompt_meta",
    "strict_mode",
]
