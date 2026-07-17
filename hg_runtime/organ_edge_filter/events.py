"""OEF runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "OEF_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "OEF_FAILED_CLOSED",
    "unknown_request": "OEF_FAILED_CLOSED",
    "missing_tep": "OEF_FAILED_CLOSED",
    "ttl_expired": "OEF_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "OEF_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "OEF_REQUEST_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]
