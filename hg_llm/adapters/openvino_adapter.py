"""
OpenVINO (Intel iGPU/CPU) adapter using OpenVINO GenAI LLMPipeline when available.

Env: HG_OPENVINO_DEVICE=GPU|CPU|AUTO, HG_OPENVINO_MODEL_PATH=/path/to/model
When openvino_genai is not installed or model path is not set, raises RuntimeError
(NotImplementedError removed per spec).
"""

from __future__ import annotations

import logging
import os
import time
from typing import AsyncIterator, List

from hg_llm.abstraction import CompletionRequest, CompletionResponse

logger = logging.getLogger(__name__)

_OPENVINO_GENAI = None


def _get_openvino_genai():
    global _OPENVINO_GENAI
    if _OPENVINO_GENAI is None:
        try:
            import openvino_genai as og
            _OPENVINO_GENAI = og
        except ImportError:
            _OPENVINO_GENAI = False
    return _OPENVINO_GENAI if _OPENVINO_GENAI is not False else None


def _device_from_env() -> str:
    device = (os.environ.get("HG_OPENVINO_DEVICE") or "AUTO").strip().upper()
    if device not in ("GPU", "CPU", "AUTO"):
        device = "AUTO"
    return device


def _model_path() -> str | None:
    return (os.environ.get("HG_OPENVINO_MODEL_PATH") or "").strip() or None


class OpenVINOAdapter:
    """
    Adapter for OpenVINO (Intel iGPU/CPU) inference via openvino_genai.LLMPipeline.
    Requires: pip install openvino-genai, HG_OPENVINO_MODEL_PATH set.
    """

    def __init__(self) -> None:
        self._pipe = None
        self._device: str | None = None
        self._model_path: str | None = None
        self._load_time_sec: float | None = None

    def _ensure_loaded(self) -> None:
        og = _get_openvino_genai()
        if og is None:
            raise RuntimeError(
                "OpenVINO backend requires openvino-genai. Install with: pip install openvino-genai"
            )
        path = _model_path()
        if not path or not os.path.isdir(path):
            raise RuntimeError(
                "HG_OPENVINO_MODEL_PATH must be set to an existing model directory. "
                "See docs/runbooks/OPENVINO_SETUP.md"
            )
        if self._pipe is not None:
            return
        device = _device_from_env()
        if device == "AUTO":
            try:
                pipe = og.LLMPipeline(path, "GPU")
                device = "GPU"
            except Exception:
                pipe = og.LLMPipeline(path, "CPU")
                device = "CPU"
        else:
            try:
                pipe = og.LLMPipeline(path, device)
            except Exception as e:
                if device == "GPU":
                    logger.warning("OpenVINO GPU failed, falling back to CPU: %s", e)
                    pipe = og.LLMPipeline(path, "CPU")
                    device = "CPU"
                else:
                    raise
        t0 = time.perf_counter()
        self._pipe = pipe
        self._device = device
        self._model_path = path
        self._load_time_sec = time.perf_counter() - t0
        logger.info(
            "OpenVINO adapter loaded: device=%s model_path=%s load_time_sec=%.2f",
            device, path, self._load_time_sec,
        )

    def _messages_to_prompt(self, messages: List[dict]) -> str:
        parts = []
        for m in messages:
            role = (m.get("role") or "user").lower()
            content = (m.get("content") or "").strip()
            if role == "user":
                parts.append(content)
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
            elif role == "system":
                parts.append(f"System: {content}")
        return "\n\n".join(parts) if parts else ""

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self._ensure_loaded()
        prompt = self._messages_to_prompt(request.messages)
        max_tokens = request.max_tokens or 256
        temperature = request.temperature if request.temperature is not None else 0.7
        og = _get_openvino_genai()
        try:
            config = og.GenerationConfig()
            config.max_new_tokens = max_tokens
            config.temperature = temperature
        except Exception:
            config = None
        t0 = time.perf_counter()
        if config is not None:
            out = self._pipe.generate(prompt, config)
        else:
            out = self._pipe.generate(prompt, max_new_tokens=max_tokens)
        elapsed = time.perf_counter() - t0
        text = out if isinstance(out, str) else getattr(out, "text", str(out))
        num_tokens = len(text.split())  # approximate
        tokens_per_sec = num_tokens / elapsed if elapsed > 0 else 0
        logger.info(
            "OpenVINO complete: device=%s tokens_approx=%d elapsed_sec=%.2f tokens_per_sec=%.1f",
            self._device, num_tokens, elapsed, tokens_per_sec,
        )
        return CompletionResponse(
            content=text,
            usage={"prompt_tokens": 0, "completion_tokens": num_tokens, "total_tokens": num_tokens},
            model=self._model_path,
            finish_reason="stop",
        )

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        self._ensure_loaded()
        prompt = self._messages_to_prompt(request.messages)
        max_tokens = request.max_tokens or 256
        og = _get_openvino_genai()
        try:
            config = og.GenerationConfig()
            config.max_new_tokens = max_tokens
            config.temperature = request.temperature if request.temperature is not None else 0.7
        except Exception:
            config = None
        chunks: List[str] = []
        def streamer(subword: str) -> bool:
            chunks.append(subword)
            return False
        if config is not None:
            self._pipe.generate(prompt, config, streamer)
        else:
            self._pipe.generate(prompt, streamer=streamer, max_new_tokens=max_tokens)
        for c in chunks:
            yield c
