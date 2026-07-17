"""MBS runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "MBS_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "MBS_FAILED_CLOSED",
    "unknown_request": "MBS_FAILED_CLOSED",
    "missing_tep": "MBS_FAILED_CLOSED",
    "ttl_expired": "MBS_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "MBS_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "MBS_REQUEST_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]
