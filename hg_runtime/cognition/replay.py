"""Replay helpers for cognition stream events — no model invocation."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


def reconstruct_assembled_text(events: Iterable[Mapping[str, Any]]) -> str:
    """Rebuild streamed proposal text from MODEL_TOKEN_DELTA events in log order."""
    parts: list[str] = []
    for event in events:
        if event.get("type") != "MODEL_TOKEN_DELTA":
            continue
        payload = event.get("payload", {})
        if isinstance(payload, Mapping):
            parts.append(str(payload.get("token", "")))
    return "".join(parts)


def find_recorded_proposal(events: Iterable[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """Return the terminal MODEL_PROPOSAL_RECORDED event, if present."""
    recorded = None
    for event in events:
        if event.get("type") == "MODEL_PROPOSAL_RECORDED":
            recorded = event
    return recorded


__all__ = ["find_recorded_proposal", "reconstruct_assembled_text"]
