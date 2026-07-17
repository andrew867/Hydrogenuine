"""Eval providers — recorded fixtures and live adapter wiring (CT-13 LCB)."""

from __future__ import annotations

import json
import time
from typing import Iterator

from hg_runtime.cognition.fake_provider import FailingModelProvider
from hg_runtime.cognition.provider import CognitionCancelled, CognitionPrompt, CognitionTimeout, ModelProvider


class RecordedTranscriptProvider:
    """Replay a fixture transcript character-by-character without network."""

    provider_id = "recorded"

    def __init__(self, *, model_name: str, transcript: str) -> None:
        self.model_name = model_name
        self._transcript = transcript

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        for index, char in enumerate(self._transcript):
            if cancel_check():
                raise CognitionCancelled("cognition halted")
            if time.monotonic() > deadline_monotonic:
                raise CognitionTimeout("cognition timeout")
            yield char


class PartialStreamProvider:
    """Emit partial tokens then time out — for mid-stream containment eval."""

    provider_id = "partial_timeout"

    def __init__(self, *, model_name: str = "partial-timeout") -> None:
        self.model_name = model_name

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        partial = '{"kind":"interpretation","content":{"text":"partial'
        for char in partial:
            if cancel_check():
                raise CognitionCancelled("cognition halted")
            yield char
        raise CognitionTimeout("mid-stream timeout")


class GiantResponseProvider:
    """Emit an oversized response truncated by max_tokens budget."""

    provider_id = "giant"

    def __init__(self, *, model_name: str = "giant-response") -> None:
        self.model_name = model_name

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        blob = "x" * 4096
        payload = json.dumps({"kind": "reply_draft", "content": {"text": blob}}, sort_keys=True)
        for char in payload:
            if cancel_check():
                raise CognitionCancelled("cognition halted")
            if time.monotonic() > deadline_monotonic:
                raise CognitionTimeout("cognition timeout")
            yield char


class DuplicateCompletionProvider:
    """Deterministic transcript for idempotency checks."""

    provider_id = "duplicate"

    def __init__(self, *, model_name: str = "duplicate") -> None:
        self.model_name = model_name

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        text = json.dumps(
            {
                "kind": "interpretation",
                "content": {"text": f"duplicate:{prompt.trigger_event_id}"},
            },
            sort_keys=True,
        )
        for char in text:
            if cancel_check():
                raise CognitionCancelled("cognition halted")
            yield char


def build_recorded_provider(eval_spec) -> ModelProvider:
    kind = eval_spec.provider_kind
    if kind == "recorded":
        return RecordedTranscriptProvider(
            model_name=f"recorded:{eval_spec.eval_id}",
            transcript=eval_spec.recorded_transcript,
        )
    if kind == "partial_timeout":
        return PartialStreamProvider()
    if kind == "giant":
        return GiantResponseProvider()
    if kind == "failing":
        return FailingModelProvider(model_name="provider-error")
    if kind == "duplicate":
        return DuplicateCompletionProvider()
    raise ValueError(f"unsupported recorded provider kind: {kind}")


__all__ = [
    "DuplicateCompletionProvider",
    "GiantResponseProvider",
    "PartialStreamProvider",
    "RecordedTranscriptProvider",
    "build_recorded_provider",
]
