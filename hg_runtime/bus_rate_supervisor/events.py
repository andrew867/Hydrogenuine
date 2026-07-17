"""BRS runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "BRS_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "BRS_FAILED_CLOSED",
    "unknown_request": "BRS_FAILED_CLOSED",
    "toxic_input": "BRS_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "BRS_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "BRS_REQUEST_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]
