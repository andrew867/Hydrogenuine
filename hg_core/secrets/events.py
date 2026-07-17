"""RTC event emission secret guard (CT-02)."""

from __future__ import annotations

from typing import Any

from hg_core.secrets.canary import contains_canary, find_canaries_in_text
from hg_core.secrets.redact import contains_raw_secret_pattern


class SecretEmissionRefused(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def guard_event_payload(payload: dict[str, Any]) -> None:
    """Refuse event emission when payload contains canaries or raw secret patterns."""
    if not isinstance(payload, dict):
        raise SecretEmissionRefused("payload_must_be_object")

    def _walk(value: Any, path: str) -> None:
        if isinstance(value, str):
            if contains_canary(value):
                hits = find_canaries_in_text(value)
                raise SecretEmissionRefused(f"canary_in_event_payload:{path}:{hits[0]}")
            if contains_raw_secret_pattern(value):
                raise SecretEmissionRefused(f"raw_secret_in_event_payload:{path}")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                _walk(item, f"{path}.{key}")
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                _walk(item, f"{path}[{index}]")

    _walk(payload, "payload")


__all__ = ["SecretEmissionRefused", "guard_event_payload"]
