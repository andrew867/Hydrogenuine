"""NRV runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "NRV_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "NRV_FAILED_CLOSED",
    "unknown_request": "NRV_FAILED_CLOSED",
    "missing_tep": "NRV_FAILED_CLOSED",
    "ttl_expired": "NRV_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "NRV_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "NRV_REQUEST_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]
