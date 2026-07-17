"""Deterministic in-memory streaming provider for RTC cognition tests."""

from __future__ import annotations

import json
import time
from typing import Iterator

from hg_runtime.cognition.provider import CognitionCancelled, CognitionPrompt, CognitionTimeout


class FakeModelProvider:
    """Streams a deterministic JSON proposal without network I/O."""

    provider_id = "fake"
    delay_per_token_s: float = 0.0

    def __init__(self, *, model_name: str = "rtc-fake-model", delay_per_token_s: float = 0.0) -> None:
        self.model_name = model_name
        self.delay_per_token_s = delay_per_token_s

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        payload = {
            "kind": "candidate_action",
            "content": {
                "action_type": "oea_stub_log",
                "summary": f"acknowledge {prompt.trigger_type}",
                "trigger_event_id": prompt.trigger_event_id,
            },
        }
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for index, char in enumerate(text):
            if cancel_check():
                raise CognitionCancelled("cognition halted")
            if time.monotonic() > deadline_monotonic:
                raise CognitionTimeout("cognition timeout")
            if self.delay_per_token_s:
                time.sleep(self.delay_per_token_s)
            yield char
            if index % 16 == 0 and time.monotonic() > deadline_monotonic:
                raise CognitionTimeout("cognition timeout")


class FailingModelProvider:
    """Raises on first token — for offline failure-path tests."""

    provider_id = "failing"

    def __init__(self, *, model_name: str = "rtc-failing-model") -> None:
        self.model_name = model_name

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        raise RuntimeError("provider unavailable")
        yield ""  # pragma: no cover


__all__ = ["FailingModelProvider", "FakeModelProvider"]
