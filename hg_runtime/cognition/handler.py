"""Streaming cognition handler — proposal-only, zero tool handles."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from hg_runtime.cognition.config import CognitionConfig, load_cognition_config
from hg_runtime.cognition.provider import ModelProvider, build_provider
from hg_runtime.cognition.streaming import stream_proposal_drafts


class StreamingCognitionHandler:
    """RTC cognition handler that streams tokens into the event log as drafts."""

    handler_id = "rtc.cognition.streaming"

    def __init__(
        self,
        provider: ModelProvider | None = None,
        config: CognitionConfig | None = None,
    ) -> None:
        self.config = config or load_cognition_config()
        self.provider = provider or build_provider(self.config)
        self.calls = 0
        self._halted = False

    def _params(self) -> Dict[str, Any]:
        return {
            "temperature": self.config.temperature,
            "seed": self.config.seed,
            "max_tokens": self.config.max_tokens,
            "live_enabled": self.config.live_enabled,
            "offline": self.config.offline,
        }

    def propose(self, context: Mapping[str, Any]) -> List[Dict[str, Any]]:
        self.calls += 1
        if self._halted:
            return stream_proposal_drafts(
                self.provider,
                context,
                cancel_check=lambda: True,
                timeout_s=self.config.timeout_s,
                params=self._params(),
            )
        return stream_proposal_drafts(
            self.provider,
            context,
            cancel_check=lambda: self._halted,
            timeout_s=self.config.timeout_s,
            params=self._params(),
        )

    def halt(self) -> None:
        self._halted = True


__all__ = ["StreamingCognitionHandler"]
