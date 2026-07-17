"""RSP runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "RSP_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "RSP_FAILED_CLOSED",
    "unknown_request": "RSP_FAILED_CLOSED",
    "toxic_input": "RSP_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "RSP_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "RSP_REQUEST_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]
