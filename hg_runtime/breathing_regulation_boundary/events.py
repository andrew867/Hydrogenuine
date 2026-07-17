"""BRB runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "BRB_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "BRB_FAILED_CLOSED",
    "unknown_request": "BRB_FAILED_CLOSED",
    "toxic_input": "BRB_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "BRB_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "BRB_BREATH_CYCLE_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]

