"""TLB runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "TLB_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "TLB_FAILED_CLOSED",
    "unknown_request": "TLB_FAILED_CLOSED",
    "toxic_input": "TLB_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "TLB_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "TLB_TOOL_LIFECYCLE_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]

