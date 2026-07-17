"""IMS runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "IMS_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "IMS_FAILED_CLOSED",
    "unknown_request": "IMS_FAILED_CLOSED",
    "missing_tep": "IMS_FAILED_CLOSED",
    "ttl_expired": "IMS_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "IMS_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "IMS_REQUEST_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]
